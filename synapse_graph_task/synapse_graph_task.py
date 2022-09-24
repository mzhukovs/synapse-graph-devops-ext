import os, sys, subprocess
from pathlib import Path
from datetime import datetime
from typing import Final, List

artifacts: Final[List[str]] = [
    # "credential"
    # "templates",
    # "BigDataPoolReference" has no corresponding artifact folder
    "dataset",
    "dataflow",
    "integrationRuntime",
    "linkedService",
    "managedVirtualNetwork",
    "managedVirtualNetwork\default\managedPrivateEndpoint",
    "notebook",
    "sparkJobDefinition",
    "pipeline",
    "sqlscript",
    "kqlscript",
    "trigger",
]


def pip_install_dependencies(packages: List[str]):
    for package in packages:
        _ = subprocess.run(
            ["python3", "-m", "pip", "install", package],
            encoding="UTF-8",
            stdout=subprocess.PIPE,
        )


def generate_graph():
    import json, jmespath
    import flatten_json as fj
    import networkx as nx
    import itertools as it
    import re

    # region helper functions
    def copy_dict(data, strip_values=False, remove_keys=[]):
        if type(data) is dict:
            out = {}
            for key, value in data.items():
                if key not in remove_keys:
                    out[key] = copy_dict(
                        value, strip_values=strip_values, remove_keys=remove_keys
                    )
            return out
        else:
            return [] if strip_values else data

    def capitalize_first_letter(s: str) -> str:
        return s[0].upper() + s[1:]

    def add_node(
        nodes: list,
        node_name: str,
        node_type: str,
        additional_node_attribs: dict or None = None,
    ):
        node_type = capitalize_first_letter(node_type)
        if node_type.endswith("Reference"):
            node_type = node_type[0 : -len("Reference")]

        node_attribs = {"type": node_type}

        if additional_node_attribs is not None:
            node_attribs.update(additional_node_attribs)

        node = (node_name, node_attribs)
        if node not in nodes:
            nodes.append(node)

    def add_edge(edges: list, from_node: str, to_node: str, edge_attribs: dict):

        if edge_attribs is None:
            edge_attribs = {}

        # add weight if not present
        if "weight" not in edge_attribs.keys():
            edge_attribs["weight"] = 1

        edge = (from_node, to_node, edge_attribs)

        edge_exists = False
        for i, e in enumerate(edges):
            if e[0] + "|" + e[1] == edge[0] + "|" + edge[1] + "|" + str(
                edge_attribs.get("input_ref_edge", False)
            ):
                e[2]["weight"] += 1
                edge_exists = True
                break

        if not edge_exists:
            edges.append(edge)

    def simplify_graph(
        g: nx.DiGraph, node_ids_to_remove: list, with_attributes: bool = True
    ):
        """Removes nodes from a graph but preserves the connections between their predecessors and successors (i.e. the nodes they served as middle-men between).

        Args:
            g (nx.DiGraph): The NeworkX Directed Graph object to modify.
            node_ids_to_remove (list): List of node IDs which need to be removed.
        """

        for remove_node_id in node_ids_to_remove:
            replacement_edges = it.product(
                g.predecessors(remove_node_id), g.successors(remove_node_id)
            )

            # g.add_edges_from(connected_edges)
            for replacement_edge in replacement_edges:
                from_node_id = replacement_edge[0]
                to_node_id = replacement_edge[1]

                if not with_attributes:
                    add_edge(edges, from_node_id, to_node_id, None)
                else:
                    # from_node = g.nodes[from_node_id]
                    # to_node = g.nodes[to_node_id]
                    edge_attribs_from = g.edges[from_node_id, remove_node_id]
                    edge_attribs_to = g.edges[remove_node_id, to_node_id]
                    # todo: create options for how to treat attributes - e.g. take attribs based on from_node only [and use only that weight], or do merge of both sets from and to and sum weight - right now excluding other attribs
                    replacement_edge_attribs = {
                        "weight": edge_attribs_from["weight"]
                        + edge_attribs_to["weight"]
                    }
                    add_edge(edges, from_node_id, to_node_id, replacement_edge_attribs)

            g.remove_node(remove_node_id)

    def apply_node_filters(g: nx.DiGraph, node_types_to_include: list) -> None:
        nodes_to_remove = []

        for n in g.nodes.data():
            if n[1]["type"] not in node_types_to_include:
                nodes_to_remove.append(n[0])
                continue

            n_already_removed = False
            if exclude_regex:
                for regex in exclude_regex:
                    if regex and re.fullmatch(regex, n[0]) is not None:
                        nodes_to_remove.append(n[0])
                        n_already_removed = True
                        break

            if (
                not n_already_removed
                and n[1]["type"] == "Pipeline"
                and include_pipeline_regex
            ):
                if not any(
                    [
                        re.fullmatch(regex, n[0]) is not None
                        for regex in include_pipeline_regex
                        if regex
                    ]
                ):
                    nodes_to_remove.append(n[0])

        simplify_graph(g, nodes_to_remove)

        # second pass to clean up any floating objects that don't tie in to the most important objects; pipelines - but if no pipelines are in the graph already we skip (since presumably they just disabled them and are interested in a graph b/w the other object types)
        nodes_to_remove = []
        pl_nodes = [n[0] for n in g.nodes.data() if n[1]["type"] == "Pipeline"]

        # if the parameter was supplied to specifically identify the "primary" pipelines through which paths must exist, then we apply that filter now
        if require_path_to_pipeline_regex and len(require_path_to_pipeline_regex) > 0:
            pl_nodes = [
                pl_node
                for pl_node in pl_nodes
                if any(
                    [
                        re.fullmatch(regex, pl_node) is not None
                        for regex in require_path_to_pipeline_regex
                        if regex
                    ]
                )
            ]

        if len(pl_nodes) > 0:
            non_pl_nodes = [n[0] for n in g.nodes.data() if n[1]["type"] != "Pipeline"]
            for non_pl_node in non_pl_nodes:
                # can't trim the fat using g.to_undirected() with possible_paths = list(it.product(pl_nodes, [non_pl_node])) - need to handle the DS/LS switcharoo we pull for showing copy activity relations
                possible_paths = list(it.product(pl_nodes, [non_pl_node])) + list(
                    it.product([non_pl_node], pl_nodes)
                )  # cover both directions
                if not any(
                    [
                        nx.has_path(g, n_pl_pair[0], n_pl_pair[1])
                        for n_pl_pair in possible_paths
                    ]
                ):  # nx.bidirectional_dijkstra(g, n_pl_pair[0], n_pl_pair[1])
                    nodes_to_remove.append(non_pl_node)

        simplify_graph(g, nodes_to_remove)

    def add_mermaid_edge(
        mermaid: list, from_node: str, to_node: str, link_text: str = " "
    ) -> None:
        mermaid_edge = from_node + f" --> |{link_text}|" + to_node
        mermaid.append(mermaid_edge)

    def get_mermaid_md(g: nx.DiGraph, layout: str = "LR") -> str:
        mermaid_md = [":::mermaid"]
        mermaid_md.append(f"graph {layout};")

        # define css styles
        mermaid_md.append(
            """
            classDef redBorder stroke:red,stroke-width:4px;
            classDef greenBorder stroke:#0f0,stroke-width:4px;
            classDef blueBorder stroke:#1874BA,stroke-width:4px;
            classDef blueFill stroke:#1874BA,fill:#1874BA,stroke-width:4px;
            classDef lightBlueBorder stroke:#74CAE7,stroke-width:4px;
            classDef lightBlueFill stroke:#74CAE7,fill:#74CAE7,stroke-width:4px,color:black;
            classDef orangeBorder stroke:#FF6A00,stroke-width:4px;
            classDef yellowBorder stroke:yellow,stroke-width:4px;
            classDef whiteBorder stroke:white,stroke-width:4px;
            classDef purpleBorder stroke:purple,stroke-width:4px;
            classDef grayBorder stroke:gray,stroke-width:4px;
            classDef grayFill stroke:gray,fill:gray,stroke-width:4px;
        """
        )

        node_style_defs = {
            "Trigger": {
                "started": '{id}>"{name}"]:::greenBorder',
                "stopped": '{id}>"{name}"]:::redBorder',
            },
            "Pipeline": '{id}[["{name}"]]:::blueBorder',
            "LinkedService": '{id}{{{{"{name}"}}}}:::purpleBorder',
            "Dataset": '{id}["{name}"]:::lightBlueBorder',
            "Dataflow": '{id}(["{name}"]):::lightBlueFill',
            "Notebook": r'{id}[\"{name}"\]:::yellowBorder',
            "SparkJobDefinition": r'{id}[\"{name}"/]:::orangeBorder',
            "BigDataPool": '{id}[("{name}")]:::orangeBorder',
            "Sqlscript": '{id}["{name}"]:::whiteBorder',
            "Kqlscript": '{id}["{name}"]:::whiteBorder',
            "IntegrationRuntime": '{id}("{name}"):::blueFill',
            "ManagedVirtualNetwork": '{id}("{name}"):::grayFill',
            "ManagedPrivateEndpoint": '{id}("{name}"):::grayBorder',
        }

        # add legend for whichever item types are present
        mermaid_md.append("subgraph Legend")
        mermaid_md.append("direction RL;")
        node_types_present = {n[1]["type"] for n in g.nodes.data()}
        for node_type, node_format in node_style_defs.items():
            if node_type in node_types_present:
                if node_type == "Trigger":
                    mermaid_md.append(
                        node_format["started"].format(
                            id="Legend" + node_type + "Started",
                            name=node_type + " (started)",
                        )
                    )
                    mermaid_md.append(
                        node_format["stopped"].format(
                            id="Legend" + node_type + "Stopped",
                            name=node_type + " (stopped)",
                        )
                    )
                else:
                    mermaid_md.append(
                        node_format.format(id="Legend" + node_type, name=node_type)
                    )
        mermaid_md.append("end")  # end legend subgraph

        # add edge data
        for e in g.edges.data():

            from_node_attribs = g.nodes.data()[e[0]]
            from_node_type = from_node_attribs["type"]
            from_node_id = list(g.nodes.keys()).index(e[0])

            if (
                from_node_type == "Trigger"
            ):  # not checking to_node b/c nothing can depend on a trigger, only the other way around
                trigger_format = (
                    "started" if from_node_attribs["started"] == True else "stopped"
                )
                from_node = node_style_defs[from_node_type][trigger_format].format(
                    id=from_node_id, name=e[0]
                )
            else:
                from_node = node_style_defs[from_node_type].format(
                    id=from_node_id, name=e[0]
                )

            to_node_type = g.nodes.data()[e[1]]["type"]
            to_node_id = list(g.nodes.keys()).index(e[1])
            to_node = node_style_defs[to_node_type].format(id=to_node_id, name=e[1])

            # e_weight = e[2]["weight"]
            # mermaid_edge = from_node + f' --> |{(str(e_weight) if e_weight > 1 else " ")}|' + to_node
            mermaid_edge = from_node + " --> " + to_node

            mermaid_md.append(mermaid_edge)

        mermaid_md.append(":::")  # end mermaid graph definition
        return "\n".join(mermaid_md)

    # endregion

    inputs = json.loads(str(sys.argv[1]))
    synapse_dir: str = inputs["synapse_directory"]
    output_dir: str = inputs["artifact_staging_directory"]
    item_types: List[str] = [itype.strip() for itype in inputs["item_types"]]
    include_pipeline_regex: List[str] or None = inputs["include_pipeline_regex"]
    require_path_to_pipeline_regex: List[str] or None = inputs[
        "require_path_to_pipeline_regex"
    ]
    exclude_regex: List[str] or None = inputs["exclude_regex"]

    numbers_re = re.compile(
        r"\|(\d+)\|"
    )  # the flatten_json lib unfortunately treats array indices just as a regular path so we need to identify these to use them as what they are

    graph_layout = "LR"

    nodes = []
    edges = []

    for artifact_type in artifacts:
        json_paths = Path(f"{synapse_dir}/{artifact_type}").glob("*.json")
        for json_path in json_paths:

            with open(json_path, "r", encoding="UTF-8") as jf:
                artifact_def = json.loads(jf.read())

                # in case the references could be at any nested level in the json, we flatten to ensure we get them all
                artifact_def_flat = fj.flatten(artifact_def, "|")

                artifact_name = json_path.name.replace(".json", "")

                current_artifact = {
                    "referenceName": artifact_name,
                    "type": artifact_type,
                }  # same props as a reference

                node_attribs = {}
                if artifact_type == "trigger":
                    started = artifact_def["properties"]["runtimeState"] == "Started"
                    node_attribs["started"] = started

                if "description" in artifact_def["properties"].keys():
                    node_attribs["description"] = artifact_def["properties"][
                        "description"
                    ]

                if "managedPrivateEndpoint" in artifact_type:
                    artifact_type = "managedPrivateEndpoint"

                add_node(nodes, artifact_name, artifact_type, node_attribs)

                for (i, (k, v)) in enumerate(artifact_def_flat.items()):
                    if (
                        k.split("|")[-1] == "referenceName"
                    ):  # k.split('|')[-1] == "type" and str(v).endswith("Reference"):
                        ref_path = ".".join(
                            numbers_re.sub(r"[\1]|", k).split("|")[:-1]
                        )  # get the path to the parent object

                        if (
                            "logLocationSettings" not in ref_path
                        ):  # ignore logging dependencies
                            ref = jmespath.search(ref_path, artifact_def)
                            ref_name = ref["referenceName"]

                            edge_attribs = {
                                k: v
                                for k, v in ref.items()
                                if k not in ["referenceName", "type"]
                            }  # capture any additional properties as edge attributes, drop name and type since they're in the node data already

                            # add the ref in case it's not already present b/c not all objects have their own JSON file, e.g. big data pools
                            add_node(nodes, ref["referenceName"], ref["type"])

                            # if the reference is actualy an input (namely for copy activity) then we switch to show the ref as the "from" node and the current artifact as the "to" node
                            treat_ref_as_input = (
                                "inputs[" in ref_path
                                and ref["type"] == "DatasetReference"
                            )  # limiting this flipping just to datasets
                            # from_node_id =    ref_name if treat_ref_as_input else artifact_name
                            # to_node_id = artifact_name if treat_ref_as_input else ref_name

                            # todo use this to get the "from" nodes that have this edge attrib and flip the direction of the edges to their predecessors, e.g. to prevent LS from getting filtered out
                            if treat_ref_as_input:
                                edge_attribs["input_ref_edge"] = True

                            # add_edge(edges, from_node_id, to_node_id, edge_attribs)
                            add_edge(edges, artifact_name, ref_name, edge_attribs)

    DG = nx.DiGraph()
    DG.add_nodes_from(nodes)
    DG.add_edges_from(edges)

    # for (u, v, inverted) in DG.edges.data('input_ref_edge'):
    newly_flipped_edges = []
    for inv_e in [e for e in DG.edges.data() if e[2].get("input_ref_edge", False)]:
        # limit flipping to just LinkedServices
        # if DG.nodes[inv_e[1]]['type'] == 'LinkedService':

        weight_to_invert_off = inv_e[2]["weight"]
        e_attribs = {**inv_e[2], "weight": weight_to_invert_off}

        # DG.add_edge(edge_to_invert[1], edge_to_invert[0], **e_attribs)
        add_edge(newly_flipped_edges, inv_e[1], inv_e[0], e_attribs)

        # edge_to_invert[2]['weight'] -= weight_to_invert_off
        DG[inv_e[0]][inv_e[1]]["weight"] -= weight_to_invert_off

        for other_edge in DG.out_edges(inv_e[1], data=True):
            oe_attribs = {
                **other_edge[2],
                "weight": weight_to_invert_off,
                "input_ref_edge": True,
            }

            # DG.add_edge(edge_to_invert[1], edge_to_invert[0], **e_attribs)
            add_edge(newly_flipped_edges, other_edge[1], other_edge[0], oe_attribs)

            # edge_to_invert[2]['weight'] -= weight_to_invert_off
            DG[other_edge[0]][other_edge[1]]["weight"] -= weight_to_invert_off

            # DG.remove_edge(inv_e[0], inv_e[1])
            # DG.add_edge(inv_e[1], inv_e[0], **inv_e[2])

    DG.add_edges_from(newly_flipped_edges)

    apply_node_filters(DG, item_types)

    # remove any zero-weight edges and drop isolates
    DG.remove_edges_from([(u, v) for (u, v, w) in DG.edges.data("weight") if w <= 0])
    DG.remove_nodes_from(list(nx.isolates(DG)))

    mermaid_md = get_mermaid_md(DG)

    filename = (
        f'{output_dir}/graph_{(str(datetime.now().strftime("%Y-%m-%d_%H-%M-%S")))}.md'
    )
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", encoding="utf-8") as outfile:
        outfile.write(mermaid_md)

    print(f"Successfully wrote Synapse Graph markdown file to: {filename}")


pip_install_dependencies(["networkx", "jmespath", "flatten_json"])
generate_graph()
