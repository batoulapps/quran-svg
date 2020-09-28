import json
from os import path, walk
from xml.dom import minidom

from scour import scour


def main():
    files = list()

    svg_dir = path.join(path.dirname(path.realpath(__file__)), "output")

    for (_, _, filenames) in walk(svg_dir):
        files.extend([x for x in filenames if x.endswith("svg")])

    items = []

    for filename in sorted(files):
        filepath = path.join(svg_dir, filename)
        doc = minidom.parse(filepath)

        page_number = int(path.splitext(filename)[0])

        # find ayah markers
        all_nodes = [
            x
            for x in doc.getElementsByTagName("g")
            if x.getAttribute("id").startswith("ayah")
            and x.getAttribute("id") != "ayah_markers"
        ]
        for node in all_nodes:
            [(_, [x, y])] = scour.svg_transform_parser.parse(
                node.getAttribute("transform")
            )
            ayah_number = int(node.getAttribute("id")[4:])
            items.append(
                {"page": page_number, "ayah": ayah_number, "x": float(x), "y": float(y)}
            )

    print(json.dumps(items))


if __name__ == "__main__":
    main()
