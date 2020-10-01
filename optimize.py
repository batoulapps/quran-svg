from math import ceil
from optparse import Values
from xml.dom import minidom, NotFoundErr
from os import walk, path
from scour import scour
from svgelements import Path
from decimal import Decimal


def is_content_node(node):
    if node.firstChild is None:
        return False
    if node.firstChild.tagName != "path":
        return False
    if (node.firstChild.hasAttribute("style") and
            "fill:#ffffff" in node.firstChild.getAttribute("style")):
        return False
    return True


def is_path(node):
    return (node.tagName == "path" and
            node.hasAttribute("d"))


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


def adjust_root_transform(node, filename):
    page_number = int(filename.replace(".svg", ""))
    horizontal_offset = "-115" if page_number % 2 == 0 else "-55"
    node.setAttribute(
        "transform", f"matrix(1.3333333,0,0,-1.3333333,{horizontal_offset},640)"
    )


def set_viewbox(node, width, height):
    node.setAttribute("width", f"{width}")
    node.setAttribute("height", f"{height}")
    node.setAttribute("viewBox", f"0 0 {width} {height}")


def optimize_opening_page(doc, filename):
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


def optimize_standard_page(doc, filename):
    set_viewbox(doc.firstChild, 345, 550)

    root_group = [x for x in doc.firstChild.childNodes if x.tagName == "g"][0]
    adjust_root_transform(root_group, filename)

    root_children = root_group.childNodes

    content_group = root_children[-1]
    content_group.setAttribute("id", "content")
    ayah_marker_group = root_children[2]
    ayah_marker_group.setAttribute("id", "ayah_markers")

    # remove decorations
    decorative_nodes = root_children[0:2] + root_children[3:-1]
    remove_nodes(decorative_nodes)


def optimize_unnecessary_nodes(doc):
    # collapse clip-path groups
    nodes = [x for x in doc.getElementsByTagName("g") if x.hasAttribute("clip-path")]
    for node in nodes:
        parent = node.parentNode
        for child in node.childNodes:
            move_node(child, parent)
    remove_nodes(nodes)

    # remove empty nodes
    nodes = [x for x in doc.getElementsByTagName("g") if len(x.childNodes) == 0]
    remove_nodes(nodes)

    root_group = doc.firstChild.firstChild
    root_children = root_group.childNodes
    ayah_marker_group = root_children[0]

    for node in [x for x in ayah_marker_group.childNodes if len(x.childNodes) > 0]:
        move_node(node.firstChild.firstChild, ayah_marker_group)
        remove_nodes([node])


def set_node_ids(doc):
    root_group = doc.firstChild.firstChild
    root_group.setAttribute("id", "root")
    root_children = root_group.childNodes

    ayah_marker_group = root_children[0]
    ayah_marker_group.setAttribute("id", "ayah_markers")

    content_group = root_children[1]
    content_group.setAttribute("id", "content")


def set_ayah_numbers(doc, ayah_offset):
    root_group = doc.firstChild.firstChild
    root_children = root_group.childNodes
    ayah_marker_group = doc.getElementById("ayah_markers")

    ayah_markers = ayah_marker_group.childNodes
    ayah_marker_group.childNodes = sorted(ayah_markers, key=ayah_sort_key)

    for node in ayah_marker_group.childNodes:
        node.setAttribute("id", f"ayah{ayah_offset}")

        # print ayah offset
        x, y = get_offset(node)

        e = doc.createElement("circle")
        e.setAttribute("cx", str(x))
        e.setAttribute("cy", str(y))
        e.setAttribute("r", "2")
        e.setAttribute("fill", "red")

        t = doc.createElement("text")
        t.setAttribute("x", str(x))
        t.setAttribute("y", str(y))
        t.setAttribute("fill", "red")
        t.appendChild(doc.createTextNode(str(ayah_offset)))

        doc.firstChild.appendChild(e)
        doc.firstChild.appendChild(t)

        ayah_offset += 1

    return ayah_offset


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
        bounding_box = Path(path_definition).bbox()
        # use path's bounding box to get the center of the ayah marker
        x += Decimal(bounding_box[0] + ((bounding_box[2] - bounding_box[0]) / 2))
        y += Decimal(bounding_box[1] + ((bounding_box[3] - bounding_box[1]) / 2))

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
    except ValueError as e:
        print(transform)
        raise e

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


def main():
    files = list()

    svg_dir = path.join(path.dirname(path.realpath(__file__)), "svg")
    output_dir = path.join(path.dirname(path.realpath(__file__)), "output")

    for (dirpath, dirnames, filenames) in walk(svg_dir):
        svg_files = [file for file in filenames if file[-4:] == ".svg"]
        files.extend(svg_files)

    ayah_offset = 1

    for filename in sorted(files):
        print(f"Opening {filename}")
        filepath = path.join(svg_dir, filename)
        doc = minidom.parse(filepath)

        if filename in ["001.svg", "002.svg"]:
            optimize_opening_page(doc, filename)
        else:
            optimize_standard_page(doc, filename)

        # remove all clip-path attributes
        all_nodes = doc.getElementsByTagName("*")
        for node in all_nodes:
            try:
                node.removeAttribute("clip-path")
            except NotFoundErr:
                pass

        doc = scour_xml(doc)

        ayah_offset = set_ayah_numbers(doc, ayah_offset)

        out_string = doc.toprettyxml()
        doc.unlink()

        with open(path.join(output_dir, filename), "w") as file:
            file.write(out_string)
            print(f"Processed {filename}")


if __name__ == "__main__":
    main()
