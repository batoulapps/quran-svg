import svgpathtools
from math import floor
from os import path, mkdir
import time
import sys

debug_mode = False
svg_dir = path.join(path.dirname(path.realpath(__file__)), "output")
determinate_ratio = 6
search_width = 10


def debug_overlay_path(page_offset, line_height, line):
    line_y = page_offset + (line * line_height)
    mid = page_offset + ((line - 0.5) * line_height)
    buffer = line_height / determinate_ratio

    top = page_offset if line == 1 else mid - buffer
    bottom = mid + (line_height / 2) if line == 15 else mid + buffer

    p = f"M 0,{top} L 345,{top} L 345,{bottom} L 0,{bottom} L 0,{top} M 0,{line_y} L 345,{line_y}"
    return svgpathtools.parse_path(p)


def indeterminate_path_info(glyph_path, page_offset, line_height):
    glyph_bounds = glyph_path.bbox()
    # (xmin, xmax, ymin, ymax)
    top_y_pos = glyph_bounds[2] - page_offset
    bottom_y_pos = glyph_bounds[3] - page_offset

    top_line = min(floor(top_y_pos / line_height) + 1, 15)
    bottom_line = min(floor(bottom_y_pos / line_height) + 1, 15)

    if top_line == bottom_line:
        if top_y_pos < ((top_line - 0.5) * line_height):
            top_line = bottom_line - 1
        else:
            bottom_line = top_line + 1

    top_distance = top_y_pos - ((top_line - 0.5) * line_height)
    bottom_distance = ((bottom_line - 0.5) * line_height) - bottom_y_pos

    return glyph_path, (top_line, bottom_line), min(top_distance, bottom_distance)


def path_distance(undetermined_path, _path):
    min_d = 999
    min_t = 999
    for i in range(0, 101):
        t_val = i * 0.01
        d = undetermined_path.radialrange(_path.point(t_val))[0][0]
        if d < min_d:
            min_d = d
            min_t = t_val
    return min_d, min_t


def detect_indeterminate_line(glyph_info, lines):
    top_line = glyph_info[1][0]
    bottom_line = glyph_info[1][1]
    glyph_path = glyph_info[0]
    glyph_box = glyph_path.bbox()
    glyph_min = glyph_box[0] - search_width
    glyph_max = glyph_box[1] + search_width

    if top_line != 1 or bottom_line != 2 or glyph_min < 250:
        return None, None

    def within_bounds(comparison_path, x_min, x_max):
        comp = comparison_path.bbox()
        left_check = x_min <= comp[0] <= x_max
        right_check = x_min <= comp[1] <= x_max
        overlap_check = comp[0] <= x_min and comp[1] >= x_max
        return left_check or right_check or overlap_check

    top_paths = lines[top_line].d().split("M")
    top_paths = filter(lambda x: len(x.strip()) > 0, top_paths)
    top_paths = map(lambda x: svgpathtools.parse_path(f"M{x}"), top_paths)
    top_paths = filter(lambda x: within_bounds(x, glyph_min, glyph_max), top_paths)
    top_paths = list(top_paths)

    bottom_paths = lines[bottom_line].d().split("M")
    bottom_paths = filter(lambda x: len(x.strip()) > 0, bottom_paths)
    bottom_paths = map(lambda x: svgpathtools.parse_path(f"M{x}"), bottom_paths)
    bottom_paths = filter(lambda x: within_bounds(x, glyph_min, glyph_max), bottom_paths)
    bottom_paths = list(bottom_paths)

    def min_distance(undetermined_path, comparison_paths):
        minimum_distance = 999999999
        nearest_point = None
        for _path in comparison_paths:
            distance, t = path_distance(undetermined_path, _path)
            if distance < minimum_distance:
                minimum_distance = distance
                nearest_point = _path.point(t)

        return minimum_distance, nearest_point

    top_distance, nearest_top_point = min_distance(glyph_path, top_paths)
    bottom_distance, nearest_bottom_point = min_distance(glyph_path, bottom_paths)

    if top_distance < bottom_distance:
        return top_line, nearest_top_point
    else:
        return bottom_line, nearest_bottom_point


def detect_line_number(glyph_bounds, page_offset, line_height):
    top_y_pos = glyph_bounds[2] - page_offset
    bottom_y_pos = glyph_bounds[3] - page_offset

    top_line = min(floor(top_y_pos / line_height) + 1, 15)
    bottom_line = min(floor(bottom_y_pos / line_height) + 1, 15)

    buffer_height = (line_height / determinate_ratio)
    top_line_mid = (top_line - 0.5) * line_height
    bottom_line_mid = (bottom_line - 0.5) * line_height

    top_line_bounds = (top_line_mid + buffer_height, top_line_mid - buffer_height)
    bottom_line_bounds = (bottom_line_mid + buffer_height, bottom_line_mid - buffer_height)

    # shortcut for line 1 if top of path is above determination point
    if top_line == 1 and top_y_pos <= top_line_bounds[0]:
        return top_line

    # shortcut for line 15 if bottom of path is below determination point
    if bottom_line == 15 and bottom_y_pos >= bottom_line_bounds[1]:
        return bottom_line

    # check if top or bottom of path is within top line determination bounds
    if top_line_bounds[0] >= top_y_pos >= top_line_bounds[1] or \
       top_line_bounds[0] >= bottom_y_pos >= top_line_bounds[1]:
        return top_line

    # check if top or bottom of path is within bottom line determination bounds
    if bottom_line_bounds[0] >= top_y_pos >= bottom_line_bounds[1] or \
       bottom_line_bounds[0] >= bottom_y_pos >= bottom_line_bounds[1]:
        return bottom_line

    # check if middle of path is within top line determination bounds
    if top_y_pos <= top_line_bounds[0] and bottom_y_pos >= top_line_bounds[1]:
        return top_line

    # check if middle of path is within bottom line determination bounds
    if top_y_pos <= bottom_line_bounds[0] and bottom_y_pos >= bottom_line_bounds[1]:
        return bottom_line

    return None


def extract_lines(filepath, page_dir):
    doc = svgpathtools.Document(filepath)
    content_group = doc.get_group([None, "content"])

    # bounds are in the format (xmin, xmax, ymin, ymax)
    page_bounds = doc.paths_from_group(content_group)[0].bbox()

    line_height = (page_bounds[3] - page_bounds[2]) / 15

    lines = {}
    debug_lines = {}
    debug_nodes = {}
    for line_number in range(1, 16):
        lines[line_number] = svgpathtools.Path()
        debug_lines[line_number] = svgpathtools.Path()
        debug_nodes[line_number] = []

    full_path = svgpathtools.Path()
    for doc_path in doc.paths():
        for sub_path in doc_path:
            full_path.append(sub_path)

    indeterminate_paths = []
    for _path in full_path.d().split("M"):
        if len(_path.strip()) > 0:
            glyph_path = svgpathtools.parse_path(f"M{_path}")
            line_number = detect_line_number(glyph_path.bbox(), page_bounds[2], line_height)
            if line_number:
                for path_command in glyph_path:
                    lines[line_number].append(path_command)
            else:
                indeterminate_paths.append(glyph_path)

    indeterminate_paths = [indeterminate_path_info(p, page_bounds[2], line_height) for p in indeterminate_paths]
    indeterminate_num = len(indeterminate_paths)
    print(f"Found {indeterminate_num} indeterminate paths")

    indeterminate_paths.sort(key=lambda x: x[2])

    for i, indeterminate_path in enumerate(indeterminate_paths):
        start_time = time.time()
        determination = detect_indeterminate_line(indeterminate_path, lines)
        if determination[0]:
            if determination[1]:
                debug_nodes[determination[0]].append(determination[1])
            for path_command in indeterminate_path[0]:
                lines[determination[0]].append(path_command)
                debug_lines[determination[0]].append(path_command)
        print(f"Completed {i+1}/{indeterminate_num} path determations in {time.time() - start_time:.2} seconds")

    attribs = {
        "fill": "#000000",
        "fill-rule": "evenodd"
    }

    debug_attribs = {
        "stroke": "#FF0000",
        "stroke-width": "0.5",
        "fill-opacity": "0"
    }

    svg_attribs = {
        "xml:space": "preserve",
        "viewBox": "0 0 345 50",
        "width": "",
        "height": ""
    }

    for svg_line in lines.items():
        if len(svg_line[1]) == 0:
            continue

        line_number = svg_line[0]
        y_pos = floor(svg_line[1].bbox()[2])
        svg_attribs["viewBox"] = f"0 {y_pos} 345 50"
        filename = path.join(page_dir, f"{line_number}.svg")

        _paths = [svg_line[1]]
        _attribs = [attribs]
        _nodes = []
        if debug_mode:
            _nodes = debug_nodes[line_number]
            if len(debug_lines[line_number]) > 0:
                _paths.append(debug_lines[line_number])
                _attribs.append(debug_attribs)

        svgpathtools.wsvg(_paths, filename=filename, attributes=_attribs, svg_attributes=svg_attribs, nodes=_nodes)

    if debug_mode:
        filename = path.join(page_dir, "debug.svg")
        debug_paths = [full_path]
        svg_attribs["viewBox"] = "0 0 345 550"
        _attribs = [attribs]
        for line in range(1, 16):
            debug_paths.append(debug_overlay_path(page_bounds[2], line_height, line))
            _attribs.append(debug_attribs)

        svgpathtools.wsvg(debug_paths, filename=filename, attributes=_attribs, svg_attributes=svg_attribs, )


def process_svg_file(page):
    start_time = time.time()

    svg_file = f"{page_number:03}.svg"
    filepath = path.join(svg_dir, svg_file)
    page_dir = path.join(svg_dir, svg_file.replace(".svg", ""))

    if not path.exists(page_dir):
        mkdir(page_dir)

    extract_lines(filepath, page_dir)

    print(f"page {svg_file} finished in {(time.time() - start_time) / 60:.2} minutes")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        try:
            page_number = int(sys.argv[1])
            if page_number > 604 or page_number < 1:
                raise ValueError('Page number out of bounds')
            process_svg_file(page_number)
        except ValueError:
            print("Invalid page number, must be an integer from 1 to 604")
    else:
        print("Usage: line_split.py PAGE_NUMBER")
