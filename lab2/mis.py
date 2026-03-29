from typing import Dict, List, Tuple
import random

Tree = Dict[int, List[int]]
DpState = Tuple[int, List[int]] 

def find_mis_in_tree(tree: Tree, root: int) -> DpState:
    """
    Finds the maximum independent set (MIS) in an undirected tree.
    """
    if not tree:
        return 0, []

    def dfs(node: int, parent: int) -> Tuple[DpState, DpState]:
        size_inc, nodes_inc = 1, [node] # If we take the node
        size_exc, nodes_exc = 0, []     # If we don't take the node
        
        for child in tree.get(node, []):
            if child == parent:
                continue # Protection from cycles
            
            child_inc, child_exc = dfs(child, node)
            
            # If we take the current node, we are obligated not to take its children
            size_inc += child_exc[0]
            nodes_inc.extend(child_exc[1])
            
            # If we don't take the current node, we are free to take its children
            if child_inc[0] > child_exc[0]:
                size_exc += child_inc[0]
                nodes_exc.extend(child_inc[1])
            else:
                size_exc += child_exc[0]
                nodes_exc.extend(child_exc[1])
                
        # Return two results: with the node and without the node
        return (size_inc, nodes_inc), (size_exc, nodes_exc)

    res_inc, res_exc = dfs(root, -1)
    return res_inc if res_inc[0] > res_exc[0] else res_exc


def generate_random_tree(n: int, seed: int = None) -> Tree:
    """
    Generates a random undirected tree with N vertices.
    """
    if seed is not None:
        random.seed(seed)
        
    tree = {i: [] for i in range(n)}
    for i in range(1, n):
        parent = random.randint(0, i - 1)
        tree[i].append(parent)
        tree[parent].append(i)
        
    return tree

def visualize_tree_mis(tree: Tree, root: int, mis_nodes: List[int]):
    """
    Draws a tree and marks the nodes that are in the MIS.
    """
    mis_set = set(mis_nodes)
    
    def print_node(node: int, parent: int, prefix: str, is_last: bool):
        marker = "[+]" if node in mis_set else "[-]"
        connector = "└── " if is_last else "├── "
        
        if parent == -1:
            print(f"{marker} {node} (Root)")
        else:
            print(f"{prefix}{connector}{marker} {node}")
            
        children = [c for c in tree.get(node, []) if c != parent]
        if parent != -1:
            prefix += "    " if is_last else "│   "
            
        for i, child in enumerate(children):
            child_is_last = (i == len(children) - 1)
            print_node(child, node, prefix, child_is_last)

    print_node(root, -1, "", True)


if __name__ == "__main__":
    N = 15
    root_node = 0
    
    random_tree = generate_random_tree(N, seed=42)
    
    mis_size, mis_nodes = find_mis_in_tree(random_tree, root_node)
    
    print(f"Size of MIS: {mis_size}")
    print(f"Nodes in MIS: {mis_nodes}\n")
    print("Tree structure ( [+] - in MIS, [-] - not in MIS ):")
    visualize_tree_mis(random_tree, root_node, mis_nodes)
