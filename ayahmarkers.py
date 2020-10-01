import json
from os import path, walk
from xml.dom import minidom, NotFoundErr, Node


def main():
    files = list()

    output_dir = path.join(path.dirname(path.realpath(__file__)), "output")

    for (_, _, filenames) in walk(output_dir):
        files.extend([x for x in filenames if x.endswith("svg")])

    items = []

    for filename in sorted(files):
        filepath = path.join(output_dir, filename)
        doc = minidom.parse(filepath)

        page_number = path.splitext(filename)[0]

        # make getElementById work
        all_nodes = doc.getElementsByTagName("*")
        for node in all_nodes:
            try:
                node.setIdAttribute("id")
            except NotFoundErr:
                pass

        # find ayah markers
        nodes = doc.getElementById("ayah_markers").childNodes
        for node in [x for x in nodes if x.nodeType == Node.ELEMENT_NODE]:
            ayah_number = node.getAttribute("ayah:index")
            x = node.getAttribute("ayah:x")
            y = node.getAttribute("ayah:y")
            items.append(
                {
                    "page": int(page_number),
                    "ayah": int(ayah_number),
                    "x": float(x),
                    "y": float(y),
                }
            )

    with open(path.join(output_dir, "markers.json"), "w") as file:
        file.write(json.dumps(items, indent=4))


if __name__ == "__main__":
    main()
