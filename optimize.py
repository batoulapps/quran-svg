import json
from math import ceil
from multiprocessing import Pool
from optparse import Values
from xml.dom import minidom, NotFoundErr, Node
from os import walk, path
from scour import scour
from svgelements import Path
from decimal import Decimal

svg_dir = path.join(path.dirname(path.realpath(__file__)), "svg")
output_dir = path.join(path.dirname(path.realpath(__file__)), "output")
surahs = []


def is_path(node):
    return (
        node.nodeType == Node.ELEMENT_NODE
        and node.tagName == "path"
        and node.hasAttribute("d")
    )


def is_group(node):
    return node.nodeType == Node.ELEMENT_NODE and node.tagName == "g"


def remove_tags(tag_names, doc):
    for tag_name in tag_names:
        elements = doc.getElementsByTagName(tag_name)
        for element in elements:
            parent = element.parentNode
            parent.removeChild(element)


def remove_nodes(nodes):
    for node in nodes:
        parent = node.parentNode
        parent.removeChild(node)


def move_node(node, new_parent):
    moving_node = node.parentNode.removeChild(node)
    new_parent.appendChild(moving_node)


def adjust_root_transform(node, page_number):
    horizontal_offset = "-115" if page_number % 2 == 0 else "-55"
    node.setAttribute(
        "transform", f"matrix(1.3333333,0,0,-1.3333333,{horizontal_offset},640)"
    )


def set_viewbox(node, width, height):
    node.setAttribute("width", f"{width}")
    node.setAttribute("height", f"{height}")
    node.setAttribute("viewBox", f"0 0 {width} {height}")


def optimize_opening_page(doc, _):
    set_viewbox(doc.firstChild, 235, 235)

    root_group = [x for x in doc.firstChild.childNodes if x.tagName == "g"][0]
    root_group.setAttribute("transform", "matrix(1.3333333,0,0,-1.3333333,-136,482)")

    root_children = root_group.childNodes

    content_group = root_children[-1]
    content_group.setAttribute("id", "content")
    ayah_marker_group = root_children[-2]
    ayah_marker_group.setAttribute("id", "ayah_markers")

    # remove decorations
    decorative_nodes = root_children[0:-2]
    remove_nodes(decorative_nodes)

    # remove nested surah title
    remove_nodes([content_group.firstChild.firstChild.lastChild])

    return None


def optimize_standard_page(doc, page_number):
    set_viewbox(doc.firstChild, 345, 550)

    root_group = [x for x in doc.firstChild.childNodes if x.tagName == "g"][0]
    adjust_root_transform(root_group, page_number)

    root_children = root_group.childNodes

    content_group = root_children[-1]
    content_group.setAttribute("id", "content")
    ayah_marker_group = root_children[2]
    ayah_marker_group.setAttribute("id", "ayah_markers")

    content_children = content_group.childNodes
    decorative_nodes = root_children[0:2] + root_children[3:-1] + content_children[0:-1]

    # figure out surah header position
    page_surahs = [x for x in surahs if x["pageNumber"] == page_number]
    if len(page_surahs) > 0:
        found = get_surah_header_positions(decorative_nodes)

        if len(found) != len(page_surahs):
            raise Exception("surah header count mismatch")

        found_sorted = sorted(found, key=lambda pair: pair[1])
        for i in range(len(page_surahs)):
            s = page_surahs[i]
            f = found_sorted[i]
            s["headerPosition"] = {
                "x": float(round(f[0], 4)),
                "y": float(round(f[1], 4)),
            }

    # remove decorations
    remove_nodes(decorative_nodes)

    return page_surahs


def get_surah_header_positions(nodes):
    found = []
    for node in nodes:
        if is_group(node):
            found.extend(get_surah_header_positions(node.childNodes))
        if is_path(node):
            path_definition = node.getAttribute("d")
            xmin, ymin, xmax, ymax = Path(path_definition).bbox()
            width, height = xmax - xmin, ymax - ymin
            if round(width) in range(245, 250) and round(height) in range(25, 30):
                x, y = get_offset(node.parentNode)
                found.append((x, y))

    return found


def set_ayah_numbers(doc):
    ayah_marker_group = doc.getElementById("ayah_markers")

    ayah_markers = ayah_marker_group.childNodes
    ayah_marker_group.childNodes = sorted(ayah_markers, key=ayah_sort_key)

    for node in ayah_marker_group.childNodes:
        # print ayah offset
        x, y = get_offset(node)

        node.setAttribute("ayah:x", str(round(x, 4)))
        node.setAttribute("ayah:y", str(round(y, 4)))


def ayah_sort_key(ayah_node):
    transform = scour.svg_transform_parser.parse(ayah_node.getAttribute("transform"))
    try:
        [(_, [x, y])] = transform
    except ValueError as e:
        print(transform)
        raise e
    return [-round_up(y, 10), -x]


def get_offset(node, x=0, y=0):
    if node.firstChild is not None and is_path(node.firstChild):
        path_definition = node.firstChild.getAttribute("d")
        xmin, ymin, xmax, ymax = Path(path_definition).bbox()
        # use path's bounding box to get the center of the ayah marker
        x += Decimal(xmin + ((xmax - xmin) / 2))
        y += Decimal(ymin + ((ymax - ymin) / 2))

    try:
        transform = scour.svg_transform_parser.parse(node.getAttribute("transform"))
        while len(transform) > 0:
            tr, vals = transform.pop()
            if tr == "translate":
                x += vals[0]
                y += vals[1]
            if tr == "matrix":
                x = vals[0] * x + vals[2] * y + vals[4]
                y = vals[1] * y + vals[3] * y + vals[5]
    except NotFoundErr:
        pass
    except AttributeError:
        pass

    if node.parentNode is not None:
        return get_offset(node.parentNode, x, y)

    return x, y


def round_up(num, divisor):
    return ceil(num / divisor) * divisor


def scour_xml(doc):
    in_string = doc.toxml()
    doc.unlink()

    options = scour.sanitizeOptions(
        Values(
            {
                "remove_descriptive_elements": True,
                "enable_viewboxing": True,
                "strip_ids": True,
                "protect_ids_list": "ayah_markers,content",
            }
        )
    )

    # scour the string
    out_string = scour.scourString(in_string, options)

    # prepare the output xml.dom.minidom object
    doc = minidom.parseString(out_string.encode("utf-8"))

    # since minidom does not seem to parse DTDs properly
    # manually declare all attributes with name "id" to be of type ID
    # (otherwise things like doc.getElementById() won't work)
    all_nodes = doc.getElementsByTagName("*")
    for node in all_nodes:
        try:
            node.setIdAttribute("id")
        except NotFoundErr:
            pass

    return doc


def process_file(filename):
    print(f"Opening {filename}")

    filepath = path.join(svg_dir, filename)
    page_number = int(path.splitext(filename)[0])

    doc = minidom.parse(filepath)

    if filename in ["001.svg", "002.svg"]:
        out = optimize_opening_page(doc, page_number)
    else:
        out = optimize_standard_page(doc, page_number)

    doc.firstChild.setAttribute("xmlns:ayah", "https://quranapp.com")

    # remove all clip-path attributes
    all_nodes = doc.getElementsByTagName("*")
    for node in all_nodes:
        try:
            node.removeAttribute("clip-path")
        except NotFoundErr:
            pass

    doc = scour_xml(doc)
    doc.firstChild.setAttribute("xmlns:ayah", "https://quranapp.com/svg")

    set_ayah_numbers(doc)

    out_string = doc.toxml()
    doc.unlink()

    with open(path.join(output_dir, filename), "w") as file:
        file.write(out_string)
        print(f"Processed {filename}")

    return out


def main():
    with open("surah.json") as fp:
        surahs.extend(json.load(fp))

    files = []

    for (_, _, filenames) in walk(svg_dir):
        svg_files = [file for file in filenames if file[-4:] == ".svg"]
        files.extend(svg_files)

    with Pool() as p:
        updated_surahs = p.map(process_file, files)

    for page_surahs in [x for x in updated_surahs if x is not None]:
        for surah in page_surahs:
            surahs[surah["number"]-1] = surah

    with open(path.join(output_dir, "surah.json"), "w") as fp:
        json.dump(surahs, fp, indent=4, sort_keys=True)


if __name__ == "__main__":
    main()
