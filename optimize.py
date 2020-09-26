from xml.dom import minidom
from os import walk, path

def isContentNode(node):
    if node.firstChild == None:
        return False
    if node.firstChild.tagName != 'path':
        return False
    if node.firstChild.hasAttribute('style') and 'fill:#ffffff' in node.firstChild.getAttribute('style'):
        return False
    return True

def removeNodeWithName(nodeName, xml):
    nodes = xml.getElementsByTagName(nodeName)
    for node in nodes:
        parent = node.parentNode
        parent.removeChild(node)

def adjustRootTransform(node, filename):
    page_number = int(filename.replace('.svg', ''))
    horizontal_offset = '-115' if page_number % 2 == 0 else '-55'
    node.setAttribute('transform', f'matrix(1.3333333,0,0,-1.3333333,{horizontal_offset},640)')

def setViewBox(node, width, height):
    node.setAttribute('width', f'{width}')
    node.setAttribute('height', f'{height}')
    node.setAttribute('viewBox', f'0 0 {width} {height}')

def optimizeOpeningPage(xml, filename):
    setViewBox(xml.firstChild, 235, 235)
    
    main_node = xml.firstChild.firstChild
    main_node.setAttribute('transform', f'matrix(1.3333333,0,0,-1.3333333,-136,482)')
    
    top_groups = main_node.childNodes

    content_group = top_groups[len(top_groups) - 1]
    ayah_markers = top_groups[len(top_groups) - 2] # todo parse ayah markers to record ayah end positions
    to_remove = top_groups[0:len(top_groups) - 1]

    for node in to_remove:
        parent = node.parentNode
        parent.removeChild(node)
    
    group_nodes = content_group.getElementsByTagName('g')
    translated_group = [x for x in group_nodes if x.hasAttribute('transform')][-1]
    node = translated_group.parentNode.removeChild(translated_group)
    main_node.appendChild(node)

    content_group.parentNode.removeChild(content_group)

def optimizeStandardPage(xml, filename):
    setViewBox(xml.firstChild, 345, 550)
    
    main_node = xml.firstChild.firstChild
    adjustRootTransform(main_node, filename)

    top_groups = main_node.childNodes

    content_group = top_groups[len(top_groups) - 1]
    ayah_markers = top_groups[len(top_groups) - 2] # todo parse ayah markers to record ayah end positions
    to_remove = top_groups[0:len(top_groups) - 1]

    for node in to_remove:
        parent = node.parentNode
        parent.removeChild(node)
    
    group_nodes = content_group.getElementsByTagName('g')
    translated_groups = [x for x in group_nodes if isContentNode(x)]
    
    for translated_group in translated_groups:
        node = translated_group.parentNode.removeChild(translated_group)
        main_node.appendChild(node)

    content_group.parentNode.removeChild(content_group)

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

        removeNodeWithName('metadata', xml)
        removeNodeWithName('defs', xml)
        
        if filename in ['001.svg', '002.svg']:
            optimizeOpeningPage(xml, filename)
        else:
            optimizeStandardPage(xml, filename)

        output = xml.toxml()
        xml.unlink()

        output_path = path.join(output_dir, filename)
        file_handler = open(output_path,'w')
        file_handler.write(output)
        file_handler.close()
        print(f'Processed {filename}')


if __name__ == "__main__":
    main()