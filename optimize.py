from xml.dom import minidom
from os import walk, path

def removeNodeWithName(nodeName, xml):
    nodes = xml.getElementsByTagName(nodeName)
    for node in nodes:
        parent = node.parentNode
        parent.removeChild(node)

files = list()

svg_dir = path.join(path.dirname(path.realpath(__file__)), "svg")
output_dir = path.join(path.dirname(path.realpath(__file__)), "output")

for (dirpath, dirnames, filenames) in walk(svg_dir):
    files.extend(filenames)

for filename in sorted(files):
    print(f'Opening {filename}')
    filepath = path.join(svg_dir, filename)
    xml = minidom.parse(filepath)

    removeNodeWithName('metadata', xml)
    removeNodeWithName('defs', xml)

    main_node = xml.firstChild.firstChild

    top_groups = main_node.childNodes

    content_group = top_groups[len(top_groups) - 1]
    ayah_markers = top_groups[len(top_groups) - 2] # todo parse ayah markers to record ayah end positions
    to_remove = top_groups[0:len(top_groups) - 1]

    for node in to_remove:
        parent = node.parentNode
        parent.removeChild(node)
    
    group_nodes = content_group.getElementsByTagName('g')
    translated_group = [x for x in group_nodes if x.hasAttribute('transform')][0]
    node = translated_group.parentNode.removeChild(translated_group)
    main_node.appendChild(node)

    content_group.parentNode.removeChild(content_group)

    output = xml.toxml()
    xml.unlink()

    output_path = path.join(output_dir, filename)
    file_handler = open(output_path,'w')
    file_handler.write(output)
    file_handler.close()
    print(f'Processed {filename}')