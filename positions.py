import json
from os import path, walk
from xml.dom import minidom, NotFoundErr, Node


def generate_positions():
    files = list()

    output_dir = path.join(path.dirname(path.realpath(__file__)), "output")

    for (_, _, filenames) in walk(output_dir):
        files.extend([x for x in filenames if x.endswith("svg")])

    with open("surah.json") as fp:
        surahs = json.load(fp)

    surah_index = 0
    ayah_number = 0

    for filename in sorted(files):
        filepath = path.join(output_dir, filename)
        doc = minidom.parse(filepath)

        page_number = int(path.splitext(filename)[0])

        # make getElementById work
        all_nodes = doc.getElementsByTagName("*")
        for node in all_nodes:
            try:
                node.setIdAttribute("id")
            except NotFoundErr:
                pass

        items = []

        # find ayah markers
        nodes = doc.getElementById("ayah_markers").childNodes
        for node in [x for x in nodes if x.nodeType == Node.ELEMENT_NODE]:
            ayah_number += 1
            x = node.getAttribute("ayah:x")
            y = node.getAttribute("ayah:y")
            items.append(
                {
                    "surahNumber": surahs[surah_index]["number"],
                    "ayahNumber": ayah_number,
                    "x": float(x),
                    "y": float(y),
                }
            )

            if ayah_number == surahs[surah_index]["ayahCount"]:
                ayah_number = 0
                surah_index += 1

        with open(path.join(output_dir, f"{page_number:03}.json"), "w") as fp:
            json.dump(items, fp, indent=4, sort_keys=True)


if __name__ == "__main__":
    generate_positions()
