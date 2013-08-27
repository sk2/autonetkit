//TODO: see if can use underscore.js for other operations, to simplify mapping, iterationl etc
//List concat based on http://stackoverflow.com/questions/5080028
//

var g_groupings = chart.append("svg:g")
.attr("id", "g_groupings");

var g_links = chart.append("svg:g")
.attr("id", "g_links");

var g_link_highlights = chart.append("svg:g")
.attr("id", "g_link_highlights");

var g_nodes = chart.append("svg:g")
.attr("id", "g_nodes");

var g_node_labels = chart.append("svg:g")
.attr("id", "g_node_labels");




var g_link_labels = chart.append("svg:g")
.attr("id", "g_link_labels");

var g_traces = chart.append("svg:g")
.attr("id", "g_highlights");

var g_highlights = chart.append("svg:g")
.attr("id", "g_highlights");

var g_path_node_annotation_backings = chart.append("svg:g")
.attr("id", "g_path_node_annotation_backings");

var g_path_node_annotations = chart.append("svg:g")
.attr("id", "g_path_node_annotations");


var g_interfaces = chart.append("svg:g")
.attr("id", "g_interfaces");

//To store svg defs for icons
chart.append("defs")

var icon_width = 45;
var icon_height = 45;

var jsondata;

var ws = new WebSocket(socket_url);
ws.onopen = function() {
    ws.send("overlay_list");
    ws.send("overlay_id=" + overlay_id);
    $("#websocket_icon").html(' <i class="icon-circle " title="WebSocket Connected."></i>');
};
ws.onclose = function () {
    $("#websocket_icon").html(' <font color ="red"> <i class="icon-remove-sign " title="WebSocket Disconnected. Reload page to reconnect."></i></font>');
};


//TODO: make "phy" default selected

var nodes_by_id = {};

var pathinfo = [];

var graph_history = [];
var ip_allocations = [];

var node_label_id = "label";
var edge_group_id = ""; //TODO: rename edge_label_id
var interface_label_id = "";

var interface_overlay_groupings = {
    'ospf': 'area',
    'vrf': 'vrf_name',
}

starting_hosts = [];

ws.onmessage = function (evt) {
    var data = jQuery.parseJSON(evt.data);
    //TODO: parse to see if valid traceroute path or other data
    if ("graph" in data) {
        if (overlay_id != "ip_allocations"){
            jsondata = data;
            graph_history.push(data);
            update_title();
            revision_id = graph_history.length - 1;
            propagate_revision_dropdown(graph_history); //TODO: update this with revision from webserver
            ip_allocations = [];
            filtered_nodes= []; //reset filtering
            redraw_ip_allocations();
            redraw();
        }
    }
    else if("path" in data) {
        pathinfo.push(data['path']);
        status_label.html("Path: " + data['path']);
        redraw_paths();
    }
    else if("overlay_list" in data) {
        propagate_overlay_dropdown(data['overlay_list']);
    }
    else if("starting" in data) {
        status_label.html("Starting: " + data['starting']);
        node_id = data['starting'];
        node = nodes_by_id[node_id];
        if (node != null) {
            starting_hosts = [node];
            //starting_hosts.push(node);
        }

        redraw();
    }
    else if("lab started" in data) {
        status_label.html("Lab started on: " + data['lab started']);
    }
    else if("ip_allocations" in data) {
        ip_allocations = data['ip_allocations'];
        if (overlay_id == "ip_allocations") {
            //Only redraw if currently selected
            jsondata.nodes = [];
            jsondata.links = [];
            redraw();
            redraw_ip_allocations();
        }
    }
    else if("highlight" in data) {
        apply_highlight(data['highlight']);
    }
    else {
        console.log("Received unknown data", data);
        //TODO: work out why reaching here if passing the "graph in data" check above
    }
}

highlight_nodes = [];
highlight_edges = [];

var apply_highlight = function(data){

    highlight_nodes = _.map(data['nodes'], function(n) {
        return nodes_by_id[n];
    })

    highlight_edges = _.map(data['edges'], function(n) {
        //Put into same form as json.links
        src = nodes_by_id[n[0]];
        src_index = nodes.indexOf(src);
        target = nodes_by_id[n[1]];
        target_index = nodes.indexOf(target);

        return {'source': src_index, 'target': target_index};
    })

    if ((data.nodes.length > 0) || (data.edges.length > 0)) {
        redraw();
    }


    //draw paths after redraw -> z-ordering means overlayed
    //pathinfo = []; //reset
    if (data.paths.length > 0) {
        for (index in data.paths) {
            path = data.paths[index];
            //path_nodes = _.map(path, function(n) {
                //return nodes_by_id[n];
            //})
            pathinfo.push(path);
        }
        redraw_paths();
    }
}

var load_ip_allocations = function(d) {

}

var ip_node_info = function(d) {
    var children = "" ;

    for (index in d.children) {
        child = d.children[index];
        children += "(" + child.name + ", " + child.subnet + ") ";
    }
    return d.name + ": " + d.subnet + " children: " + children;
}

function redraw_ip_allocations() {
    //adapated from http://mbostock.github.com/d3/talk/20111018/tree.html
    var diagonal = d3.svg.diagonal()
        // change x and y (for the left to right tree)
        //.projection(function(d) { return [d.y + 100, d.x]; });
        .projection(function(d) { return [d.y + 80, d.x]; });

    var layout = d3.layout.tree().size([700,500]);

    var nodes = layout.nodes(ip_allocations);
    if (ip_allocations.length == 0) {
        nodes = []; //otherwise have single root node always present
    }

    var node = g_nodes.selectAll("g.node")
        .data(nodes, name)
        node.enter().append("svg:g")
        .attr("transform", function(d) { return "translate(" + (d.y + 80) + "," + d.x +  ")"; })

        var nodeEnter = node.enter().append("svg:g")
        .attr("class", "node")
        .attr("transform", function(d) { return "translate(" + (d.y + 80) + "," + d.x +  ")"; });

    nodeEnter.append("svg:circle")
        .attr("class", "ip_node")
        .attr("r", 1e-6)
        .attr("fill", "steelblue")
        .on("mouseover", function(d){
            d3.select(this).style("fill", "orange");
        })
    .on("mouseout", function(){
        d3.select(this).style("fill", "steelblue");
    });

    $('.ip_node').tipsy({
        //based on http://bl.ocks.org/1373263
        gravity: 'w',
        html: true,
        title: function() {
            var d = this.__data__
        return ip_node_info(d);
        }
    });


    var nodeUpdate = node.transition()
        .duration(500)
        .attr("transform", function(d) { return "translate(" + (d.y + 80) + "," + d.x + ")"; });

    //TODO: fix issue with node names

    nodeUpdate.select("circle")
        .attr("r", 6);
    //TODO: map colour to node type: edge, collision domain, subnet, l3_device

    // Add the dot at every node
    var nodeExit = node.exit().transition()
        .duration(500)
        .attr("transform", function(d) { return "translate(" + (d.y + 80) + "," + d.x + ")"; })
        .remove();

    nodeExit.select("circle")
        .attr("r", 1e-6);

    nodeEnter.append("svg:text")
        .attr("x", function(d) { return d.children || d._children ? -15 : 15; })
        .attr("dy", ".3em")
        .attr("text-anchor", function(d) { return d.children || d._children ? "end" : "start"; }) //left if children otherwise right
        .attr("font-family", "helvetica")
        .attr("font-size", 10)
        .text(function(d) { return d.name; })
        .style("fill-opacity", 1e-6);

    nodeUpdate.select("text")
        .text(function(d) { return d.name; })
        .style("fill-opacity", 1);

    nodeExit.select("text")
        .style("fill-opacity", 1e-6);

    // Update the links…
    var link = g_links.selectAll("path.link")
        .data(layout.links(nodes, name), function(d) { return d.target.id; });

    // Enter any new links at the parent's previous position.
    link.enter().insert("svg:path", "g")
        .attr("class", "link")
        .attr("d", diagonal)
        .transition()
        .duration(500)
        .attr("d", diagonal);

    // Transition links to their new position.
    link.transition()
        .duration(500)
        .attr("d", diagonal);

    // Transition exiting nodes to the parent's new position.
    link.exit().transition()
        .duration(500)
        .attr("d", diagonal)
        .style("opacity", 1e-6)
        .remove();
}

var propagate_overlay_dropdown = function(d) {
    $("#overlay_select").empty();
    d.push('ip_allocations'); //manually append as not in graph overlay list
    overlay_dropdown
        .selectAll("option")
        .data(d)
        .enter().append("option")
        .attr("value", String)
        .text(String);

    //TODO only set the first time around?
    $("#overlay_select option[value=" + overlay_id + "]").attr("selected", "selected")
}

var propagate_revision_dropdown = function(d) {
    revisions = d3.range(graph_history.length);

    if (revisions.length > 1) {
        $('#revision_select').show();
    } else {
        $('#revision_select').hide();
    }

    revision_dropdown
        .selectAll("option")
        .data(revisions)
        .enter().append("option")
        .attr("value", String)
        .text(String);

    $("#revision_select option[value=" + revision_id + "]").attr("selected", "selected")
}

var propagate_node_label_select = function(d) {
    $("#node_label_select").empty();
    d.unshift("None"); //Add option to clear edge labels
    node_label_select
        .selectAll("option")
        .data(d)
        .enter().append("option")
        .attr("value", String)
        .text(String);

    //TODO only set the first time around?
    $("#node_label_select option[value=" + node_label_id + "]").attr("selected", "selected")
}

var propagate_interface_label_select = function(d) {
    $("#interface_label_select").empty();

    d.unshift("None"); //Add option to clear edge labels

    interface_label_select
        .selectAll("option")
        .data(d)
        .enter().append("option")
        .attr("value", String)
        .text(String);

    //TODO only set the first time around?
    $("#interface_label_select option[value=" + interface_label_id + "]").attr("selected", "selected")
}

var propagate_edge_group_select = function(d) {
    //TODO: make default "none" and don't group?
    $("#edge_group_select").empty();

    d.unshift("None"); //Add option to clear edge labels

    var dropdown = edge_group_select
        .selectAll("option")
        .data(d)

        dropdown.enter().append("option")
        .attr("value", String)
        .text(String);

    //TODO only set the first time around?
    $("#edge_group_select option[value=" + edge_group_id + "]").attr("selected", "selected")
}

var print_each_revision = false;

var load_revision = function() {
    update_title();
    jsondata = graph_history[revision_id];
    $("#revision_select option[value=" + revision_id + "]").attr("selected", "selected")
        if (print_each_revision) {
            window.print();
        }
}

//dropdown.select("phy").text("selected");

var clear_label = function() {
    status_label.html("");
}

var trace_paths = g_highlights.append("svg:g")
.attr("id", "path");

var nodes = d3.map;

var icon = function(d) {
    var filename = "icons/" + d.device_type;
    if (d.device_subtype != null && d.device_subtype != "None") {
        filename += "_" + d.device_subtype;
    }
    filename += ".svg";
    return filename;
}

var source_x = function(d) {
    return nodes[d.source].x + x_offset + icon_width/2;
}
var source_y = function(d) {
    return nodes[d.source].y  + y_offset+ icon_height/2;
}

var target_x = function(d) {
    return nodes[d.target].x + x_offset + icon_width/2;
}
var target_y = function(d) {
    return nodes[d.target].y  + y_offset+ icon_height/2;
}

var label = function(d) {
    return d.id;
}

var asn = function(d) {
    return d.asn;
}

var link_type = function(d) {
    return d.type;
}

var edge_id = function(d) {
    return d.edge_id;
}


var update_title = function() {
    document.title = "AutoNetkit - " + overlay_id + " r" + revision_id;
}

var clear_graph_history = function() {
    graph_history = [];
    propagate_revision_dropdown(graph_history); //TODO: update this with revision from webserver
}


//TODO: replace all 32 magic numbers with icon_offset
var icon_offset = icon_width/2;

var x_offset = 10;
var y_offset = 30;

var node_x = function(d) {
    return d.x + x_offset + icon_width/2;
}

var node_y = function(d) {
    return d.y + y_offset + icon_height/2;
}

// based on http://bl.ocks.org/2920551
var fill = d3.scale.category20b();

var edge_stroke_colors = d3.scale.ordinal();

var edgeStroke = function(d, i) { return fill(d); };

var interface_angle = function(d){
    //common to interface_x and interface_y
    s_x = node_x(d.node);
    s_y = node_y(d.node);
    t_x = node_x(d.target);
    t_y = node_y(d.target);

    angle = Math.atan2( (t_x - s_x), (t_y - s_y));
    return angle;
}


var interface_width = 15;
var interface_height = 10;

var interface_hypotenuse = (icon_width + icon_height)/2;

var interface_x = function(d) {

    if (jsondata.directed) {
        return directed_edge_offset_x(d.node, d.target, interface_hypotenuse) - interface_width/2;
    }

    angle = interface_angle(d);
    offset_x = interface_hypotenuse * Math.sin(angle);
    return node_x(d.node) + offset_x - interface_width/2;
}

var interface_y = function(d) {

    if (jsondata.directed) {
        return directed_edge_offset_y(d.node, d.target, interface_hypotenuse) - interface_height/2;
    }

    angle = interface_angle(d);
    offset_y =interface_hypotenuse * Math.cos(angle);
    return node_y(d.node) + offset_y - interface_height/2;
}

var groupPath = function(d) {

    if (display_interfaces && overlay_id in interface_overlay_groupings) {
        if (d.values.length  == 1) {
            //This shouldn't occur for single ospf interface!
            node = d.values[0];
            offset = 2;
            retval =  "M" ;
            retval += (interface_x - offset  + icon_offset + x_offset) + "," + (interface_y - offset + icon_offset + y_offset) + "L";
            retval += (interface_x + offset  + icon_offset + x_offset) + "," + (interface_y - offset + icon_offset + y_offset) + "L";
            retval += (interface_x - offset  + icon_offset + x_offset) + "," + (interface_y + offset + icon_offset + y_offset) + "L";
            retval += (interface_x + offset + icon_offset + x_offset) + "," + (interface_y + offset + icon_offset + y_offset);
            retval += "Z";
            return retval
        } else if (d.values.length  == 2) {
            interface1 = d.values[1];
            interface2 = d.values[0];
            //Note: upper_x goes with lower_y due to y ascending down, x ascending right
            int1_x = interface_x(interface1);
            int1_y = interface_y(interface1);
            int2_x = interface_x(interface2);
            int2_y = interface_y(interface2);
            upper_x = Math.max(int1_x, int2_x);
            upper_y = Math.max(int1_y, int2_y);
            lower_x = Math.min(int1_x, int2_x);
            lower_y = Math.min(int1_y, int2_y);

            offset = 0.1;
            retval =  "M" ;
            retval += (upper_x - offset ) + "," + (upper_y - offset ) + "L";
            retval += (upper_x + offset ) + "," + (upper_y - offset ) + "L";
            retval += (lower_x + offset ) + "," + (lower_y + offset ) + "L";
            retval += (lower_x - offset ) + "," + (lower_y + offset ) ;
            retval += "Z";
            return retval;
        } else {
            interface_offset = 5;
            retval = "M" +
                d3.geom.hull(d.values.map(function(i) {
                    return [interface_x(i) + interface_offset, interface_y(i) + interface_offset];
                }))
            .join("L")
                + "Z";
            return retval;
        }
        return;
    }

    if (d.values.length  == 1) {
        node = d.values[0];
        offset = 5;
        retval =  "M" ;
        retval += (node.x - offset  + icon_offset + x_offset) + "," + (node.y - offset + icon_offset + y_offset) + "L";
        retval += (node.x + offset  + icon_offset + x_offset) + "," + (node.y - offset + icon_offset + y_offset) + "L";
        retval += (node.x - offset  + icon_offset + x_offset) + "," + (node.y + offset + icon_offset + y_offset) + "L";
        retval += (node.x + offset + icon_offset + x_offset) + "," + (node.y + offset + icon_offset + y_offset);
        retval += "Z";
        return retval
    }
    else if (d.values.length  == 2) {
        //TODO: here we should return a path enclosing either the one or both nodes
        //TODO: need to make sure that node1 comes before node2?
        node1 = d.values[1];
        node2 = d.values[0];
        //Note: upper_x goes with lower_y due to y ascending down, x ascending right
        ////TODO: do these get over written?
        upper_x = Math.max(node1.x, node2.x);
        upper_y = Math.max(node1.y, node2.y);
        lower_x = Math.min(node1.x, node2.x);
        lower_y = Math.min(node1.y, node2.y);
        upper_node = node1;
        lower_node = node2;
        if (node2.x < node1.x) {
            upper_node = node2;
            lower_node = node1;
        }
        //TODO: adjust offsets depending if nodes aligned / or \
        upper_x = upper_node.x;
        upper_y = upper_node.y;
        lower_x = lower_node.x;
        lower_y = lower_node.y;
        offset = 0.1;
        retval =  "M" ;
        retval += (upper_x - offset  + icon_offset + x_offset) + "," + (upper_y - offset + icon_offset + y_offset) + "L";
        retval += (upper_x + offset + icon_offset + x_offset) + "," + (upper_y - offset + icon_offset + y_offset) + "L";
        retval += (lower_x + offset + icon_offset + x_offset) + "," + (lower_y + offset + icon_offset + y_offset) + "L";
        retval += (lower_x - offset + icon_offset + x_offset) + "," + (lower_y + offset + icon_offset + y_offset) ;
        retval += "Z";
        return retval;
    }
    retval = "M" +
        d3.geom.hull(d.values.map(function(i) { return [i.x + x_offset + icon_width/2, i.y + y_offset + icon_height/2]; }))
        .join("L")
        + "Z";
    return retval;
}

var path_x = function(d) {
    node = nodes_by_id[d];
    return node.x + icon_width/2 + x_offset;
}

var path_y = function(d) {
    node = nodes_by_id[d];
    return node.y+ icon_height/2 + y_offset;
}

var data_to_li = function(d, depth) {
    //TODO: may want to limit recursion depth
    max_depth = 1;
    text = "<ul>"; //begin the unordered list
    for (attr in d) {
        if(_.isArray(d[attr])) {
            text += "<li><b>" + attr + ":</b> ";
            text += d[attr].join(", ");
        }
        else if (attr == "_interfaces") {
            //text += "<li><b>Interfaces: </b> ";
            //text += _.keys(d[attr]).join(", ");
        }
        else if (typeof d[attr] == 'object' && d[attr] != null && depth < max_depth) {
            text += data_to_li(d[attr], depth +1); // recurse
        }
        else {
            text += "<li><b>" + attr + ":</b> " + d[attr] + "</li>"; //add the key/val
        }
    }
    text += "<ul>"; //finish the unordered list
    return text;

}

//TODO: make recursive, if type is object and not null then call, and repeat...
var node_info = function(d) {
    //TODO: append ul/li like table example on http://christopheviau.com/d3_tutorial/
    text = d.id;
    text += data_to_li(d, 0);
    text = "<b>Node</b>: " + text;
    return text;
    //status_label.html(text);
}

var path_info = function(d) {
    status_label.html("Path: " + d);
}

var link_info = function(d) {
    source = nodes[d.source];
    target = nodes[d.target];
    text = source.id + " - " + target.id; //TODO: make sure all have labels from graphics appended overlay

    for (attr in d) {
        //TODO use list membership test here instead
        if (d[attr] != null && d[attr] != "None" && attr != "source" & attr != "target" && attr != "_interfaces" && attr != "edge_id") {
            text += ", " + attr + ": " + d[attr];
        }
    }
    text = "Link: " + text;
    return text;
    //status_label.html(text);
}

var interface_info = function(d) {
    int_data = d.node._interfaces[d.interface];

    text = "<ul>"; //begin the unordered list
    text += "<li><b>node:</b> " + d.node.id + "</li>"; //add the key/val
    text += "<li><b>interface:</b> " + d.interface + "</li>"; //add the key/val
    for (attr in int_data) {
        text += "<li><b>" + attr + ":</b> " + int_data[attr] + "</li>"; //add the key/val
    }
    text += "<ul>"; //finish the unordered list
    text = "<b>Interface</b>: " + text;
    return text;
}

//Markers from http://bl.ocks.org/1153292
// Used for arrow-heads
// Per-type markers, as they don't inherit styles.
//TODO: create separate markers for traces and links
//TODO: set marker properties by css
//g_traces.append("svg:defs").selectAll("marker")
//TODO: check this still works
chart.select("defs").selectAll("marker")
.data(["path_marker", "path_verified_marker", "path_unverified_marker"])
.enter().append("svg:marker")
.attr("id", String)
.attr("refX", 2.4)
.attr("refY", 2)
//.attr("fill", "rgb(25,52,65)")
//.attr("stroke", "rgb(25,52,65)")
.attr("markerWidth", 20)
.attr("markerHeight", 10)
//.attr("markerUnits", "userSpaceOnUse")
.attr("orient", "auto")
.append("svg:path")
.attr("d", "M0,0 V4 L2,2 Z");

var marker_end  = function(d) {
    if (jsondata.directed) {
        return "url(#path_marker)";
    }
    return "";
}

var d3LineBasis = d3.svg.line().interpolate("basis");
var offsetScale = 0.15; /* percentage of line line to offset curves */
var radius = 20;

var alpha = 0.2;

var graph_edge = function(d) {
    var source_x = nodes[d.source].x + x_offset + icon_width/2;
    source_y =  nodes[d.source].y + y_offset + icon_height/2;
    target_x =  nodes[d.target].x + x_offset + icon_width/2;
    target_y =  nodes[d.target].y + y_offset + icon_height/2;

    if (jsondata.directed) {
        var dx = target_x - source_x,
            dy = target_y - source_y,
               dr = Math.sqrt(dx * dx + dy * dy);
        //dr = 1.2 * dr;
        //return "M" + source_x + "," + source_y + "A" + dr + "," + dr + " 0 0,1 " + target_x + "," + target_y;
        var points = [];
        points.push([source_x, source_y]);

        dr = dr/2; //want to place point halfway


        //TODO: experiment with alpha being based on node distance
        //alpha = alpha + alpha * dr/8000;

        angle = Math.atan2( (target_x - source_x), (target_y - source_y));
        angle = angle + alpha;
        h2 = dr / Math.cos(alpha);
        offset_x = h2 * Math.sin(angle);
        offset_y = h2 * Math.cos(angle);

        points.push([source_x + offset_x, source_y + offset_y]);

        points.push([target_x, target_y]);
        return d3LineBasis(points) ;
    } else {
        //TODO: look at join for here
        return  "M" + source_x + "," + source_y + "L" + target_x + "," + target_y;
    }
}

var directed_edge_offset_x = function(source, target, hypotenuse) {
    //multiplier is how far out to return, ie the hypotenuse. Used as don't want interfaces co-incident with link labels
    //TODO: want interfaces to be fixed distance out, regardless of dr

    s_x = node_x(source);
    s_y = node_y(source);
    t_x = node_x(target);
    t_y = node_y(target);

    dx = t_x - s_x;
    dy = t_y - s_y;
    dr = Math.sqrt(dx * dx + dy * dy);

    hypotenuse = typeof hypotenuse !== 'undefined' ? hypotenuse : dr/4; //defaults to dr/4

    angle = Math.atan2( (t_x - s_x), (t_y - s_y));
    angle = angle + alpha;
    offset_x = hypotenuse * Math.sin(angle);
    return s_x + offset_x;
}

var directed_edge_offset_y = function(source, target, hypotenuse) {
    //multiplier is how far out to return, ie the hypotenuse. Used as don't want interfaces co-incident with link labels

    s_x = node_x(source);
    s_y = node_y(source);
    t_x = node_x(target);
    t_y = node_y(target);

    dx = t_x - s_x;
    dy = t_y - s_y;
    dr = Math.sqrt(dx * dx + dy * dy);

    hypotenuse = typeof hypotenuse !== 'undefined' ? hypotenuse : dr/4; //defaults to dr/4

    angle = Math.atan2( (t_x - s_x), (t_y - s_y));
    angle = angle + alpha;
    offset_y = hypotenuse * Math.cos(angle);
    return s_y + offset_y;
}

var link_label_x = function(d) {

    var source_x = nodes[d.source].x + x_offset + icon_width/2;
    source_y =  nodes[d.source].y + y_offset + icon_height/2;
    target_x =  nodes[d.target].x + x_offset + icon_width/2;
    target_y =  nodes[d.target].y + y_offset + icon_height/2;
    //TODO: update undirected case to use node_x and node_y
    //
    if (jsondata.directed) {
        source = nodes[d.source];
        target = nodes[d.target];
        return directed_edge_offset_x(source, target);
    } else {
        var source_x = nodes[d.source].x + x_offset + icon_width/2;
        target_x =  nodes[d.target].x + x_offset + icon_width/2;
        return (source_x + target_x) /2;
    }
}

var link_label_y = function(d) {

    source = nodes[d.source];
    target = nodes[d.target];

    if (jsondata.directed) {
        source = nodes[d.source];
        target = nodes[d.target];
        return directed_edge_offset_y(source, target);
    }  else {
        source_y =  nodes[d.source].y + y_offset + icon_height/2;
        target_y =  nodes[d.target].y + y_offset + icon_height/2;
        return (source_y + target_y) /2;
    }
}


var node_attr_groups;
var edge_attr_groups;
var revision_id = 0;

var status_label = d3.select(".infobar").append("text")
.attr("class", "status label")
.attr("y", 15)
.attr("x", 0)
.attr("font-size", "14")
.text("")
;

var history_start = function() {
    revision_id = 0;
    load_revision();
    redraw();
}

var history_end = function() {
    revision_id = graph_history.length - 1;
    load_revision();
    redraw();
}

var history_back = function() {
    if (revision_id - 1 >= 0) {
        revision_id--;
        load_revision();
        redraw();
    } else {
        //status_label.text("Already at first revision");
    }
}

//TODO: check difference between var a = function(), and function a()... is former d3?
var history_forward = function() {
    if ((revision_id + 1) < graph_history.length) {
        revision_id++;
        load_revision();
        redraw();
    } else {
        //status_label.text("Already at latest revision");
    }
}


$(document).keydown(function(e){
    switch(e.which) {
        case 37: // left
            history_back();
            break;

        case 38: // up
            break;

        case 39: // right
            history_forward();
            break;

        case 40: // down
            break;

        default: return; // exit this handler for other keys
    }
    e.preventDefault();
});


//TODO: group attr needs to return an index based on the overlay... this could be more than one attribute, eg OSPF is ASN and area.
//
var group_attr = "asn";

var group_info = function(d) {
    if (overlay_id in interface_overlay_groupings) {
        //string tuple of "asn,grouping_attr"
        var data = d.key.split(",");
        text = ("Group: <ul><li>" + data[0] +  "</li><li>area: " + data[1] + "</li></ul>");
    } else {
        text = ("Group: " + group_attr + " " + d.key);
    }
    return text;
    //status_label.html(text);
}

var node_group_id = function(d) {

    group_attr = "asn";
    if (overlay_id == "nidb") {
        group_attr = "host";
    }
    else if (overlay_id == "conn") {
        group_attr = "device";
    }
    else if (overlay_id == "vrf") {
        group_attr = "vrf";
    }
    else if (overlay_id in interface_overlay_groupings) {
        //TODO: don't want to have (asn, vrf) tuple for vrfs: just want (vrf)
        attr = interface_overlay_groupings[overlay_id];
        return ([d['asn'], d[attr]]);
    }
    else if (overlay_id == "bgp" || overlay_id == "ibgp_v4" || overlay_id == "ibgp_v6") {
        return (["ASN " + d['asn'], d['ibgp_l3_cluster'], d['ibgp_l2_cluster']]);
    }

    return d[group_attr];

}

var device_label = function(d) {
    return d[node_label_id];
}

var interface_label = function(d) {
    try {
        int_data = d.node._interfaces[d.interface];
        return int_data[interface_label_id];
    }
    catch (err) {
        //console.log(err);
        //console.log("error for", d.node.id, d.interface);
    }
}

var zoom_fit = function() {
    if (jsondata.nodes.length) {
        //rescale if showing nodes, rather than the ip allocs, etc
        node_x_max = _.max(nodes, function(node){ return node.x}).x + icon_width/2 + 20;
        node_y_max = _.max(nodes, function(node){ return node.y}).y + icon_height/2 + 20;

        p =  Math.max((chart_width/node_x_max)/2, (chart_height/node_y_max)/2);
        p = p * 1.5;

        var zoom_box = d3.select(".zoom_box")

            zoom_box.transition()
            .attr("transform", "scale(" + p + ")")
            .duration(500)
            //redraw();
    }
}

var filtered_nodes = [];

function numeric_strings_to_float(array){
    array = _.map(array, function(x) {
        if ($.isNumeric(x.value)) x.value = parseFloat(x.value); //float if numeric
        return x;
    });
    return array;
}

function serialized_array_to_grouped_list(array) {
    array = _.groupBy(array, function(x) { return x.name});
    //extract out grouped items to format: [['asn', [1, 2, 3,]]], etc
    array = _.map(array, function(group_items, key, l) {
        return [key, _.map(group_items, function(item){ return item.value})];
    });
    return array;
}

function applyNodeFilter() {
    test = $("#nodeFilterForm").serializeArray(); //obtain form values

    //convert numeric strings to floats for eg asn comparisons
    test = numeric_strings_to_float(test);
    test = serialized_array_to_grouped_list(test);

    f_nodes = nodes; //list of nodes to iteratively trim
    test.forEach(function(x) {
        attribute = x[0];
        values = x[1];
        f_nodes = _.filter(f_nodes, function(node) {
            return _.contains(values, node[attribute]); //keep node if attribute in values list
        });
    });

    filtered_nodes = f_nodes; //set the global
    redraw();
}

var icon_opacity = function(x) {
    if (filtered_nodes.length == 0) return 1; //no filtered, so display all at full opacity
    if (_.contains(filtered_nodes, x)) return 1; //some are filtered, full opacity for these
    return 0.2; //drop opacity for non filtered
};

var interface_opacity = function(x) {
    if (filtered_nodes.length == 0) return 1;
    //no filtered, so display all at full opacity

    if (_.contains(filtered_nodes, x.node))
    {
        return 1;
    }//some are filtered, full opacity for these
    return 0.2; //drop opacity for non filtered
};

var line_opacity = function(x) {
    if (filtered_nodes.length == 0) return 1; //no filtered, so display all at full opacity

    source = nodes[x.source];
    target = nodes[x.target];

    if (_.contains(filtered_nodes, source) && _.contains(filtered_nodes, target)) return 1; //some are filtered, full opacity for these
    return 0.2; //drop opacity for non filtered
};


// Store the attributes used for nodes and edges, to allow user to select
var node_attributes = [];
var edge_attributes = [];

function redraw() {
    //TODO: tidy this up, not all functions need to be in here, move out those that do, and only pass required params. also avoid repeated calculations.

    nodes = jsondata.nodes;

    node_attributes = []; //reset
    nodes.forEach(function(node) {
        nodes_by_id[node.id] = node;
        node_attributes.push.apply(node_attributes, _.keys(node));
    });

    //TODO: add support for color for edge id edge_group_id


    //TODO: sort then make unique
    node_attributes.sort();
    node_attributes = _.uniq(node_attributes);
    propagate_node_label_select(node_attributes);

    //TODO: combine with node attributes to just take the keys from the groupby for efficiency
    node_attribute_unique_values = [];
    node_attributes.forEach(function(attribute) {
        values = _.uniq(_.pluck(nodes, attribute));
        node_attribute_unique_values.push([attribute, values]);
    });

    // apply these to form
    skip_attributes = Array("_interfaces", "None", "id", "label", "x", "y");
    filtered_attributes = _.reject(node_attribute_unique_values, function(x){
        if (x[1].length == 1 && x[1][0] == null) return true; // don't display attributes that are only null
        if (x[1].length > 10) return true; // don't display attributes for long lists
        return _.contains(skip_attributes, x[0]); //reject attributes in skip_attributes
    });

    var form = '<b>' + "<i class='icon-filter '></i> " + 'Filter:</b><br>';
    form += '<form action="javascript:applyNodeFilter()" id="nodeFilterForm" name="nodeFilterForm">';
    form += "<table>";
    previous_form_values = $("#nodeFilterForm").serializeArray();
    previous_form_values = numeric_strings_to_float(previous_form_values);
    previous_form_values = serialized_array_to_grouped_list(previous_form_values);
    previous_form_values = _.object(previous_form_values);

    filtered_attributes.forEach(function(unique_attribute) {
        var key = unique_attribute[0];
        var values = unique_attribute[1];
        values = values.sort();
        form += "<tr>";
        form += "<td><b>" + key + "</b></td><td>";
        values.forEach(function(val) {
            form += '<input type=checkbox name=' + key + ' value=' + val ;
            if (key in previous_form_values && _.contains(previous_form_values[key], val)) {
                form += " checked ";
            }
            form += '>' + val;
        });
        form += "</td></tr>";
        //form += "<br>";

    });
    //form += '<button onclick="javascript:applyNodeFilter();">Apply</button>';
    form += "</table>";
    form += '<input type="submit" name="submit" class="button" id="submit_btn" value="Apply" />  ';
    form += '</form>';

    $(".node_filter").html(form);

    edge_attributes = []; //reset
    jsondata.links.forEach(function(link) {
        node_attributes.push.apply(edge_attributes, _.keys(link));
    });
    edge_attributes.sort();
    edge_attributes = _.uniq(edge_attributes);
    propagate_edge_group_select(edge_attributes);

    interface_attributes = [];

    //TODO: make this a memoized function to save computation
    interface_attributes = _.map(nodes, function(node) {
        return _.map(node._interfaces, function(interface){
            return _.keys(interface);
        });
    });
    //collapse from hierarchical nested structure
    interface_attributes_flattened = _.flatten(interface_attributes);
    interface_attributes_unique = _.uniq(interface_attributes_flattened);
    propagate_interface_label_select(interface_attributes_unique);

    node_attr_groups = d3.nest().key( node_group_id ).entries(nodes);
    edge_attr_groups = d3.nest().key(function(d) { return d[edge_group_id]; }).entries(jsondata.links);
    //TODO: use edge attr groups for edge colours

    //If undirected graph, then need two interfaces per edge: one at each end
    if (display_interfaces) {
        //Undirected, need to handle for both src and dst
        interface_data = _.map(jsondata.links, function(link) {
            interface_data = link._interfaces;
            src_node = nodes[link.source];
            dst_node = nodes[link.target];
            src_int_id = interface_data[src_node.id]; //interface id is indexed by the node id
            dst_int_id = interface_data[dst_node.id]; //interface id is indexed by the node id

            //Check for null interace ids: some nodes may not have interfaces (eg a collision domain)

            //TODO: if a directed link, only return for source
            //
            retval = [];
            if (src_int_id != null) {
                retval.push( { 'node': src_node, 'interface':  src_int_id, 'target': dst_node, 'link': link });
            }

            if (!jsondata.directed && dst_int_id != null) {
                //undirected, also include data for other interface
                retval.push( { 'node': dst_node, 'interface':  dst_int_id, 'target': src_node, 'link': link });
            }

            return retval;

        });

        interface_data = _.flatten(interface_data); //collapse from hierarchical nested structure
    } else {
        interface_data = {}; //reset
    }


    var interface_area = function(d) {
        //TODO: should this only be called if display_interfaces && overlay_id in interface_overlay_groupings?
        interface_id = d.interface;
        asn = d.node['asn'];
        attr = interface_overlay_groupings[overlay_id];
        area = d.node._interfaces[interface_id][attr];
        return asn + "," + area;
    }

    interface_attr_groups = d3.nest().key( interface_area ).entries(interface_data);

    if (display_interfaces && overlay_id in interface_overlay_groupings) {
        node_attr_groups = interface_attr_groups;
    }

    var hull_stroke_width = function() {
        if (display_interfaces && overlay_id in interface_overlay_groupings) {
            return 25;
        }
        return 80;
    }

    group_size = _.size(node_attr_groups)
    //TODO: make this a max function
    range_group_size = group_size;
    if (group_size < 3) {
        range_group_size = 3; // for colorbrewer
    }
    var fill = d3.scale.quantize()
    .domain([0, group_size])
    .range(colorbrewer.RdYlBu[range_group_size]);
    var groupFill = function(d, i) { return fill(i); };

    //TODO: make group path change/exit with node data
    groupings = g_groupings.selectAll(".attr_group")
        .data(node_attr_groups)

        groupings.enter().insert("path")
        .attr("class", "attr_group")
        .attr("d", groupPath)
        .style("fill", groupFill)
        .style("stroke", groupFill)
        .style("stroke-width", hull_stroke_width)
        .style("stroke-linejoin", "round")
        .style("opacity", 0.3)
        .on("mouseover", function(d){
            group_info(d);
        })
    .on("mouseout", function(){
        clear_label();
    });
    ;
    groupings.transition()
        .duration(500)
        .attr("d", groupPath)
        .style("stroke-width", hull_stroke_width)

        groupings.exit().transition()
        .duration(1000)
        .style("opacity",0)
        .remove();

    $('.attr_group').tipsy({
        //based on http://bl.ocks.org/1373263
        gravity: 'w',
        html: true,
        title: function() {
            var d = this.__data__
        return group_info(d);
        }
    });

    //TODO: filter the json data x and y ranges: store in nodes, and use this for the image plotting

    node_highlight = g_highlights.selectAll(".node_highlight")
        .data(highlight_nodes, function(d) { return d.id;})

        node_highlight.enter().append("svg:rect")
        .attr("class", "node_highlight")
        .attr("width", icon_width + 20 )
        .attr("height", icon_height + 20)
        .style("stroke", "red")
        .style("stroke-width", 2)
        .style("fill", "none")
        .attr("x", function(d) { return d.x + x_offset - 20/2; })
        .attr("y", function(d) { return d.y + y_offset - 20/2; })
        .style("opacity", 40)

        node_highlight
        .transition()
        .style("opacity", 100)
        .duration(500)

        node_highlight.exit().transition()
        .duration(1000)
        .style("opacity",0)
        .remove();


    var line = g_links.selectAll(".link_edge")
        .data(jsondata.links,
                function(d) { return d.source + "_" +  d.target})

        //line.enter().append("line")
        line.enter().append("svg:path")
        .attr("class", "link_edge")
        .style("opacity", line_opacity)
        //.attr("id",
                //function(d) {
                    //return "path"+d.source+"_"+d.target;
                //})
    .attr("d", graph_edge)
        .style("stroke-width", function() {
            //TODO: use this stroke-width function on mouseout too
            if (jsondata.directed) {
                return 2;
            }
            return 2;
        })
    //.attr("marker-end", marker_end)
    //.style("stroke", "rgb(103,109,244)")
    .style("stroke", "rgb(2,106 ,155)")
        //.style("fill", "rgb(113,119,254)")
        .style("fill", "none")

        .on("mouseover", function(d){
            d3.select(this).style("stroke", "orange");
            d3.select(this).style("fill", "none");
            d3.select(this).style("stroke-width", "2");
            d3.select(this).attr("marker-end", "");
            link_info(d);
        })
    .on("mouseout", function(){
        d3.select(this).style("stroke-width", "2");
        //d3.select(this).style("stroke", "rgb(103,109,244)");
        d3.select(this).style("stroke", "rgb(2,106 ,155)");
        d3.select(this).style("fill", "none");
        //d3.select(this).attr("marker-end", marker_end);
        clear_label();
    })

    line.transition()
        .duration(500)
        .attr("d", graph_edge)
        .style("opacity", line_opacity)

        line.exit().transition()
        .duration(1000)
        .style("opacity",0)
        .remove();

    $('.link_edge').tipsy({
        //based on http://bl.ocks.org/1373263
        gravity: 'w',
        html: true,
        title: function() {
            var d = this.__data__
        return link_info(d);
        }
    });


    var highlight_line = g_link_highlights.selectAll(".highlight_line")
        .data(highlight_edges)

        //line.enter().append("line")
        highlight_line.enter().append("svg:path")
        .attr("class", "highlight_line")
        .attr("id",
                function(d) {
                    return "path"+d.source+"_"+d.target;
                })
    .attr("d", graph_edge)
        .style("stroke-width", function() {
            //TODO: use this stroke-width function on mouseout too
            if (jsondata.directed) {
                return 5;
            }
            return 5;
        })
    //.attr("marker-end", marker_end)
    .style("stroke", "red")
        //.style("fill", "rgb(113,119,254)")
        .style("fill", "none")

        highlight_line.transition()
        .duration(500)
        .attr("d", graph_edge)
        .style("opacity", line_opacity)

        highlight_line.exit().transition()
        .duration(1000)
        .style("opacity",0)
        .remove();

    starting_circles = chart.selectAll(".starting_circle")
        .data(starting_hosts, function(d) { return d.id;})

        starting_circles.enter().append("svg:circle")
        .attr("class", "starting_circle")
        .attr("r", 30)
        .style("opacity",40)
        .attr("cx", function(d) { return d.x + x_offset + icon_width/2 ; })
        .attr("cy", function(d) { return d.y + y_offset + icon_height/2; })

        starting_circles.transition()
        .attr("r", 60)
        .style("opacity",0)
        .duration(4000);

    interface_icons = g_interfaces.selectAll(".interface_icon")
        //.data(interface_data) //TODO: check if need to provide an index
        //TODO: check if should return tuple of interface, node for uniqueness (esp for switching overlays)
        .data(interface_data, function(d) { return (d.node, d.interface);})

        var highlight_interfaces = function(d) {
            interfaces = d3.selectAll(".interface_icon");
        }

    //TODO: fix issue with interface id changing -> interfaces appear/reappear

    interface_icons.enter().append("svg:rect")
        .attr("class", "interface_icon")
        .attr("width", interface_width)
        .attr("height", interface_height)
        .attr("x", interface_x)
        .attr("y", interface_y)
        //.style("opacity", 0)

        interface_icons
        //TODO: look if can return multiple attributes, ie x and y, from the same function, ie calculation
        .attr("fill", "rgb(6,120,155)")
        //.style("opacity", 0)

        .on("mouseover", function(d){
            highlight_interfaces(d);
            d3.select(this).style("stroke", "orange");
            d3.select(this).style("fill", "yellow");
            d3.select(this).style("stroke-width", "2");
            d3.select(this).attr("marker-end", "");
        })
    .on("mouseout", function(){
        d3.select(this).style("stroke-width", "2");
        d3.select(this).style("stroke", "none");
        d3.select(this).style("fill", "rgb(6,120,155)");
        //d3.select(this).attr("marker-end", marker_end);
    })

    $('.interface_icon').tipsy({
        //based on http://bl.ocks.org/1373263
        gravity: 'w',
    html: true,
    title: function() {
        var d = this.__data__
        return interface_info(d);
    }
    });

    interface_icons.transition()
        .attr("x", interface_x)
        .attr("y", interface_y)
        //.style("opacity", interface_opacity)
        .duration(500);

    interface_icons.exit().transition()
        .duration(500)
        //.style("opacity",0)
        .remove();

    interface_labels = g_interfaces.selectAll(".interface_label")
        .data(interface_data, function(d) { return d.interface;})

        interface_labels.enter().append("text")
        .attr("x", interface_x)
        .attr("y", interface_y)
        .attr("class", "interface_label")
        .attr("text-anchor", "middle")
        .attr("font-family", "helvetica")
        //.attr("font-size", "small")
        .attr("font-size", 10)

        //TODO: use a general accessor for x/y of nodes
        interface_labels
        .attr("dx", interface_width/2) // padding-right
        .attr("dy", -interface_height + 3) // vertical-align: middle
        .text(interface_label);

    interface_labels.transition()
        .attr("x", interface_x)
        .attr("y", interface_y)
        .duration(500)

        interface_labels.exit().transition()
        .duration(500)
        .style("opacity",0)
        .remove();

    //Link labels
    link_labels = g_link_labels.selectAll(".link_label")
        .data(jsondata.links, edge_id)

        link_labels.enter().append("text")
        .attr("x",link_label_x)
        .attr("y", link_label_y )
        .attr("class", "link_label")
        .attr("text-anchor", "middle")
        .attr("font-family", "helvetica")
        .attr("font-size", "small")

        //TODO: use a general accessor for x/y of nodes
        link_labels
        .attr("dx", 0) // padding-right
        .attr("dy", 0) // vertical-align: middle
        .text(function (d) {
            if (edge_group_id == "_interfaces") {
                retval = "";
                for (attr in d[edge_group_id]) {
                    retval += "(" + attr + ", " + d[edge_group_id][attr] + ")";
                }
                return retval;
            }
            return d[edge_group_id];
        });

    link_labels.transition()
        .attr("x",link_label_x)
        .attr("y", link_label_y )
        .duration(500)

        link_labels.exit().transition()
        .duration(1000)
        .style("opacity",0)
        .remove();

    var node_id = function(d) {
        return d.label + d.network;
    }

    var node_icon = function(d) {
        retval = d.device_type;
        if (d.device_subtype != null && d.device_subtype != "None") {
            retval += "_" + d.device_subtype;
        }
        return retval;
    }

    //Append any new device icons found
    device_type_subtypes = _.map(nodes, node_icon);
    device_type_subtypes = _.uniq(device_type_subtypes);
    chart.select("defs")
        .selectAll(".icondef")
        .data(device_type_subtypes, function(d){  return d;})
        .enter()
        .append("image")
        .attr("class", "icondef")
        .attr("xlink:href", function (d){ return "icons/" + d + ".svg";})
        .attr("id", function(d) {return "icon_" + d})
        .attr("width", icon_width)
        .attr("height", icon_height);

    var image = g_nodes.selectAll(".device_icon")
        //.attr("xlink:href", icon)
        .data(nodes, function(d) { return d.id});

    image.enter().append("use")
        .attr("class", "device_icon")
        .attr("xlink:href", function(d) {return "#icon_" + node_icon(d)})
        .attr("x", function(d) { return d.x + x_offset; })
        .attr("y", function(d) { return d.y + y_offset; })
        .style("opacity", icon_opacity)
        .attr("width", icon_width)
        .attr("height", icon_height)
        .on("mouseover", function(d){
            node_info(d);
            //d3.select(this).attr("xlink:href", icon); //TODO: check why need to do this
        })
    .on("mouseout", function(){
        clear_label();
    })
    .append("svg:title")
        .text(function(d) { return d.id; })

        image
        .attr("width", icon_width)
        .attr("height", icon_height)
        .transition()
        .style("opacity", icon_opacity)
        .attr("x", function(d) { return d.x + x_offset; })
        .attr("y", function(d) { return d.y + y_offset; })
        .duration(500)

        image.exit().transition()
        .duration(1000)
        .style("opacity",0)
        .remove();

    $('.device_icon').tipsy({
        //based on http://bl.ocks.org/1373263
        gravity: 'w',
        html: true,
        title: function() {
            var d = this.__data__
        return node_info(d);
        }
    });

    device_labels = g_node_labels.selectAll(".device_label")
        .data(nodes, function(d) { return d.id});

        device_labels.enter().append("text")
        .attr("x", function(d) { return d.x + x_offset; })
        .attr("y", function(d) { return d.y + y_offset + 3; } )
        .attr("class", "device_label")
        .attr("text-anchor", "middle")
        .attr("font-family", "helvetica")
        .style("opacity", icon_opacity)
        .attr("font-size", "small")

        //TODO: use a general accessor for x/y of nodes
        device_labels
        .attr("dx", icon_width/2) // padding-right
        .attr("dy", icon_height + 3) // vertical-align: middle
        .text(device_label);

    device_labels.transition()
        .attr("x", function(d) { return d.x + x_offset; })
        .attr("y", function(d) { return d.y + y_offset + 3; })
        .style("opacity", icon_opacity)
        .duration(500)

        device_labels.exit().transition()
        .duration(1000)
        .style("opacity",0)
        .remove();
    //});


        //reset paths
        pathinfo = [];
        redraw_paths();
        }

var node_annotation = function(d) {
    //TODO: iterate over node, concatenate items
    //use host first, then others
    retval = "";
    for (attr in d) {
        if (attr != "host") {
            retval += attr + ": " + d[attr] + "  ";
        }
    }
    return retval;
}

function draw_path_node_annotations(data) {
    if ('host_info' in data){

    }
    else {
        return;
    }

    var host_info = data['host_info'];

    var annotation_x = function(host_id) {
        return nodes_by_id[host_id].x;
    }

    var annotation_y = function(host_id) {
        return nodes_by_id[host_id].y;
    }

    path_node_annotation_backings = g_path_node_annotation_backings.selectAll(".path_node_annotation_backing")
        .data(host_info, function(d) { return d.host});

    path_node_annotation_backings.enter().append("rect")
        .attr("x", function(d) { return annotation_x(d.host) + x_offset - icon_width/2; })
        .attr("y", function(d) { return annotation_y(d.host) + y_offset + icon_height/2; } )
        .attr("height", 50)
        .attr("width", 120)
        .attr("class", "path_node_annotation_backing")
        .attr("fill", "white")
        .style("opacity", 0.8)

        path_node_annotation_backings.exit().transition()
        .duration(500)
        .style("opacity",0)
        .remove();

    path_node_annotations = g_path_node_annotations.selectAll(".path_node_annotation")
        .data(host_info, function(d) { return d.host});

    path_node_annotations.enter().append("text")
        .attr("x", function(d) { return annotation_x(d.host) + x_offset; })
        .attr("y", function(d) { return annotation_y(d.host) + y_offset + 3; } )
        .attr("class", "path_node_annotation")
        .attr("text-anchor", "middle")
        .attr("font-family", "helvetica")
        .attr("background-color", "red")
        //.style("opacity", 1)
        .attr("font-size", 18)

        //TODO: use a general accessor for x/y of nodes
        path_node_annotations
        .attr("dx", icon_width/2) // padding-right
        .attr("dy", icon_height + 3) // vertical-align: middle
        .text(node_annotation);

    path_node_annotations.transition()
        .attr("x", function(d) { return annotation_x(d.host) + x_offset; })
        .attr("y", function(d) { return annotation_y(d.host) + y_offset + 3; })
        .duration(500)

        path_node_annotations.exit().transition()
        .duration(500)
        .style("opacity",0)
        .remove();

}

function redraw_paths() {

    //animation based on http://bl.ocks.org/duopixel/4063326
    var svg_line = d3.svg.line()
        .x(path_x)
        .y(path_y)
        .interpolate("cardinal")
        .tension(0.8)
        ;

    trace_path = g_traces.selectAll(".trace_path")
        .data(pathinfo, function(path) {
            elements = path['path'];
            return _.first(elements) + "_" + _.last(elements);;
        })

    var path_total_length = function(d) {
        return d.node().getTotalLength()
    }

    var path_marker_end = function(d) {
        if ("verified" in d && d['verified'] == true) {
            return "url(#path_verified_marker)";
        }
        else if ("verified" in d && d['verified'] == false) {
            return "url(#path_un_verified_marker)";
        }
        return "url(#path_marker)";
    }

    var path_color = function(d) {
        if ("verified" in d && d['verified'] == true) {
            return "green";
        }
        if ("verified" in d && d['verified'] == false) {
            return "red";
        }
        return "black";
    }

    var transition_time = function(d) {
        return 200* _.size(d.path);
    }

    trace_path.enter().append("svg:path")
        .attr("d", function(d) { return svg_line(d['path'])})
        .attr("class", "trace_path")
        .style("stroke-width", 5)
        .style("stroke", "orange")
        .style("fill", "none")
        .attr("stroke-dasharray", function(d) {
            return path_total_length(d3.select(this)) + " " + path_total_length(d3.select(this))})
        .attr("stroke-dashoffset", function(d) {
            return path_total_length(d3.select(this))})

        trace_path
        .transition()
        .style("stroke", path_color)
        .attr("d", function(d) { return svg_line(d['path'])})
        .ease("linear")
        .attr("stroke-dashoffset", 0)
        .duration(transition_time)
        .transition()
        .attr("stroke-dasharray", "0")
        .attr("marker-end", path_marker_end)
        .duration(1)

        trace_path
          .on("mouseover", function(d){
            draw_path_node_annotations(d);
            d3.select(this).style("stroke", "red");
            d3.select(this).style("stroke-width", "4");
            //path_info(d);
        })
    .on("mouseout", function(){
        d3.select(this).style("stroke-width", "3");
        d3.select(this).style("stroke", path_color);
        draw_path_node_annotations({'host_info': []});
        //clear_label();
    })


    trace_path.exit().transition()
    .duration(1000)
    .style("opacity",0)
    .remove();

}
