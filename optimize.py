from xml.dom import minidom
from os import walk, path

def is_content_node(node):
    if node.firstChild == None:
        return False
    if node.firstChild.tagName != 'path':
        return False
    if node.firstChild.hasAttribute('style') and 'fill:#ffffff' in node.firstChild.getAttribute('style'):
        return False
    return True

def remove_tags(tag_names, xml):
    for tag_name in tag_names:
        elements = xml.getElementsByTagName(tag_name)
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
    page_number = int(filename.replace('.svg', ''))
    horizontal_offset = '-115' if page_number % 2 == 0 else '-55'
    node.setAttribute('transform', f'matrix(1.3333333,0,0,-1.3333333,{horizontal_offset},640)')

def set_viewbox(node, width, height):
    node.setAttribute('width', f'{width}')
    node.setAttribute('height', f'{height}')
    node.setAttribute('viewBox', f'0 0 {width} {height}')

def optimize_opening_page(xml, filename):
    set_viewbox(xml.firstChild, 235, 235)
    
    root_group = xml.firstChild.firstChild
    root_group.setAttribute('transform', f'matrix(1.3333333,0,0,-1.3333333,-136,482)')
    
    root_children = root_group.childNodes
    
    border_group = root_children[0]
    ayah_marker_group = root_children[1] # todo parse ayah markers to record ayah end positions
    content_group = root_children[2]
    
    remove_nodes([border_group])
    
    content_sub_groups = content_group.getElementsByTagName('g')
    content_node = [x for x in content_sub_groups if is_content_node(x)][-1]
    move_node(content_node, root_group)
    remove_nodes([content_group])

def optimize_standard_page(xml, filename):
    set_viewbox(xml.firstChild, 345, 550)
    
    root_group = xml.firstChild.firstChild
    adjust_root_transform(root_group, filename)

    root_children = root_group.childNodes
    
    content_group = root_children[len(root_children) - 1]
    ayah_markers = root_children[2] # todo parse ayah markers to record ayah end positions
    to_remove = [root_children[0], root_children[1]] + root_children[3:len(root_children) - 1]
    
    remove_nodes(to_remove)
    
    content_sub_groups = content_group.getElementsByTagName('g')
    content_nodes = [x for x in content_sub_groups if is_content_node(x)]
    
    for content_node in content_nodes:
        move_node(content_node, root_group)

    remove_nodes([content_group])

def main():
    files = list()

    svg_dir = path.join(path.dirname(path.realpath(__file__)), "svg")
    output_dir = path.join(path.dirname(path.realpath(__file__)), "output")

    for (dirpath, dirnames, filenames) in walk(svg_dir):
        files.extend(filenames)

    for filename in sorted(files):
        print(f'Opening {filename}')
        filepath = path.join(svg_dir, filename)
        xml = minidom.parse(filepath)

        remove_tags(['metadata', 'defs'], xml)
        
        if filename in ['001.svg', '002.svg']:
            optimize_opening_page(xml, filename)
        else:
            optimize_standard_page(xml, filename)

        output = xml.toxml()
        xml.unlink()

        output_path = path.join(output_dir, filename)
        file_handler = open(output_path,'w')
        file_handler.write(output)
        file_handler.close()
        print(f'Processed {filename}')


if __name__ == "__main__":
    main()