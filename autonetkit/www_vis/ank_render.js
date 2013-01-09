//TODO: see if can use underscore.js for other operations, to simplify mapping, iterationl etc
//List concat based on http://stackoverflow.com/questions/5080028


var jsondata;
var socket_url = "ws://" + location.host + "/ws";
var ws = new WebSocket(socket_url);
ws.onopen = function() {
    ws.send("overlay_list");
    ws.send("overlay_id=" + overlay_id);
    ws.send("ip_allocations");
    status_label.html("WebSocket connected");
};
ws.onclose = function () {
    status_label.html("Warning: WebSocket disconnected");
};

var icon_width = 45;
var icon_height = 45;

//TODO: make "phy" default selected

var nodes_by_id = {};

var pathinfo = [];

var graph_history = [];
var ip_allocations = [];

var node_label_id = "id";
var edge_group_id = "";
var interface_label_id = "";

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
    } else {
        //TODO: work out why reaching here if passing the "graph in data" check above
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

    var node = chart.selectAll("g.node")
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
    var link = chart.selectAll("path.link")
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

var trace_paths = chart.append("svg:g")
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
var fill = d3.scale.category10();

var edge_stroke_colors = d3.scale.ordinal();

var groupFill = function(d, i) { return fill(i); };
var edgeStroke = function(d, i) { return fill(d); };
var groupPath = function(d) {
    if (d.values.length  == 1) {
        node = d.values[0];
        offset = 10;
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
        offset = 20;
        //TODO: tidy offsets
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
    return node.x+ icon_width/2 + x_offset;
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
        if (d[attr] != null && d[attr] != "None" && attr != "source" & attr != "target" && attr != "edge_id") {
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
chart.append("svg:defs").selectAll("marker")
.data(["link_edge"])
.enter().append("svg:marker")
.attr("id", String)
.attr("viewBox", "0 0 12 12")
.attr("refX", 35)
.attr("refY", -4.5)
.attr("overflow", "visible")
.attr("markerWidth", 7)
.attr("markerHeight", 7)
.attr("orient", "auto")
.append("svg:path")
.attr("d", "M0,-5L10,0L0,5");

var marker_end  = function(d) {
    if (jsondata.directed) {
        return "url(#link_edge)";
    }
    return "";
}

var d3LineBasis = d3.svg.line().interpolate("basis");
var offsetScale = 0.15; /* percentage of line line to offset curves */
var radius = 20;


function drawTaperedEdge(d) {
    //Note: not currently used
    //Adapted from http://bl.ocks.org/2942559

    var sourceX = nodes[d.source].x + x_offset + icon_width/2;
    sourceY =  nodes[d.source].y + y_offset + icon_height/2;
    targetX =  nodes[d.target].x + x_offset + icon_width/2;
    targetY =  nodes[d.target].y + y_offset + icon_height/2;

    // Changed from example: replaced repeated code with sourceX, targetY, etc variables
    var slope = Math.atan2((+targetY - sourceY), (+targetX - sourceX));
    var slopePlus90 = Math.atan2((+targetY - sourceY), (+targetX - sourceX)) + (Math.PI/2);

    var halfX = (sourceX + targetX)/2;
    var halfY = (sourceY + targetY)/2;

    var lineLength = Math.sqrt(Math.pow(targetX - sourceX, 2) + Math.pow(targetY - sourceY, 2));

    strength = 2.5; //fixed strength

    var MP1X = halfX + (offsetScale * lineLength + strength/3) * Math.cos(slopePlus90);
    var MP1Y = halfY + (offsetScale * lineLength + strength/3) * Math.sin(slopePlus90);
    var MP2X = halfX + (offsetScale * lineLength - strength/3) * Math.cos(slopePlus90);
    var MP2Y = halfY + (offsetScale * lineLength - strength/3) * Math.sin(slopePlus90);

    var points = [];
    points.push([(sourceX - strength*2 * Math.cos(slopePlus90)),(sourceY - strength * Math.sin(slopePlus90))]);
    points.push([MP2X,MP2Y]);
    points.push(([(targetX  + radius * Math.cos(slope)), (targetY + radius * Math.sin(slope))]));
    points.push(([(targetX  + radius * Math.cos(slope)), (targetY + radius * Math.sin(slope))]));
    points.push([MP1X, MP1Y]);
    points.push([(sourceX + strength*2 * Math.cos(slopePlus90)),(sourceY + strength * Math.sin(slopePlus90))]);

    return d3LineBasis(points) + "Z";
}

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
    if (overlay_id == "ospf") {
        var data = d.key.split(",");
        text = ("Group: <ul><li>asn: " + data[0] +  "</li><li>area: " + data[1] + "</li></ul>");
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
    if (overlay_id == "conn") {
        group_attr = "device";
    }

    if (overlay_id == "ospf") {
        return ([d['asn'], d['area']]);
    }
    if (overlay_id == "bgp") {
        return ([d['asn'], d['ibgp_l2_cluster']]);
    }

    return d[group_attr];

}

var device_label = function(d) {
    return d[node_label_id];
}

var interface_label = function(d) {
    int_data = d.node._interfaces[d.interface];
    return int_data[interface_label_id];
}

var zoom_fit = function() {
    if (jsondata.nodes.length) {
        //rescale if showing nodes, rather than the ip allocs, etc
        node_x_max = _.max(nodes, function(node){ return node.x}).x + 20;
        node_y_max = _.max(nodes, function(node){ return node.y}).y + 20;

        p =  Math.max((chart_width/node_x_max)/2, (chart_height/node_y_max)/2);

        var zoom_box = d3.select(".zoom_box")

            zoom_box.transition()
                    .attr("transform", "scale(" + p + ")")
                   .duration(500)
        //redraw();
    }
}

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
    interface_attributes = _.flatten(interface_attributes); //collapse from hierarchical nested structure
    interface_attributes = _.uniq(interface_attributes);
    propagate_interface_label_select(interface_attributes);

    if (overlay_id == "ospf") {

        //objects of {asn, area, node} for each area in each node
        // Follows decorate-sort-undecorate pattern, but for nest instead of sort
        all_areas = _.map(nodes, function(node) {
            return _.map(node.areas, function(area) {
                return {'asn': node.asn, 'area': area, 'node': node};
            });

        });
        all_areas = _.flatten(all_areas); //collapse from hierarchical nested structure

        node_attr_groups = d3.nest()
            .key(function(d) { return d.asn + "," + d.area})
            .rollup( function(d) { 
                return _.map(d, function(elem){ return elem.node; }); // extract the node from the decorated attributes
            }) 
        .entries(all_areas);

    } else {
        node_attr_groups = d3.nest().key( node_group_id ).entries(nodes);
    }
    edge_attr_groups = d3.nest().key(function(d) { return d[edge_group_id]; }).entries(jsondata.links);
    //TODO: use edge attr groups for edge colours

    //TODO: make group path change/exit with node data
    groupings = chart.selectAll(".attr_group")
        .data(node_attr_groups)

        groupings.enter().insert("path")
        .attr("class", "attr_group")
        .attr("d", groupPath)
        .style("fill", groupFill)
        .style("stroke", groupFill)
        .style("stroke-width", 80)
        .style("stroke-linejoin", "round")
        .style("opacity", 0.15)
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

    var line = chart.selectAll(".link_edge")
        .data(jsondata.links, edge_id)

        //line.enter().append("line")
        line.enter().append("svg:path")
        .attr("class", "link_edge")
        .attr("id", 
                function(d) { 
                    return "path"+d.source+"_"+d.target; 
                }) 
    .attr("d", graph_edge)
        .style("stroke-width", function() {
            //TODO: use this stroke-width function on mouseout too
            if (jsondata.directed) {
                return 2;
            } 
            return 2;
        })
    //.attr("marker-end", marker_end)
    .style("stroke", "rgb(103,109,244)")
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
        d3.select(this).style("stroke", "rgb(103,109,244)");
        d3.select(this).style("fill", "none");
        //d3.select(this).attr("marker-end", marker_end);
        clear_label();
    })

    line.transition()
        .duration(500)
        .attr("d", graph_edge)

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

    //If undirected graph, then need two interfaces per edge: one at each end
    if (display_interfaces) {
        //Undirected, need to handle for both src and dst
        interface_data = _.map(jsondata.links, function(link) {
            interface_data = link._interfaces;
            src_node = nodes[link.source];
            dst_node = nodes[link.target];
            src_int_id = interface_data[src_node.id]; //interface id is indexed by the node id
            dst_int_id = interface_data[dst_node.id]; //interface id is indexed by the node id

            //TODO: if a directed link, only return for source
            //
            retval = [];
            retval.push( { 'node': src_node, 'interface':  src_int_id, 'target': dst_node, 'link': link });

            if (!jsondata.directed) {
                //undirected, also include data for other interface
                retval.push( { 'node': dst_node, 'interface':  dst_int_id, 'target': src_node, 'link': link });
                }

            return retval;

        });

        interface_data = _.flatten(interface_data); //collapse from hierarchical nested structure
    } else {
        interface_data = {}; //reset 
    }

    //TODO: handle removing of interfaces

    //TODO: handling if no interface id specified

    interface_icons = chart.selectAll(".interface_icon")
        //.data(interface_data) //TODO: check if need to provide an index
        .data(interface_data, function(d) { return d.interface;})

        var interface_width = 15;
        var interface_height = 10;

        var interface_angle = function(d){
            //common to interface_x and interface_y
            s_x = node_x(d.node);
            s_y = node_y(d.node);
            t_x = node_x(d.target);
            t_y = node_y(d.target);

            angle = Math.atan2( (t_x - s_x), (t_y - s_y));
            return angle;
        }

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
        
        var highlight_interfaces = function(d) {
            interfaces = d3.selectAll(".interface_icon");
            //interfaces.filter(

        }

        interface_icons.enter().append("svg:rect")
            .attr("class", "interface_icon")
            .attr("width", interface_width)
            .attr("height", interface_height)
            .attr("x", interface_x)
            .attr("y", interface_y)

            interface_icons
            //TODO: look if can return multiple attributes, ie x and y, from the same function, ie calculation
            .attr("fill", "rgb(6,120,155)")

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
            .duration(500);

        interface_icons.exit().transition()
            .duration(500)
            .style("opacity",0)
            .remove();

        interface_labels = chart.selectAll(".interface_label")
        .data(interface_data, function(d) { return d.interface;})
        
        interface_labels.enter().append("text")
        .attr("x", interface_x)
        .attr("y", interface_y)
        .attr("class", "interface_label")
        .attr("text-anchor", "middle") 
        .attr("font-family", "helvetica") 
        .attr("font-size", "small") 

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

        link_labels = chart.selectAll(".link_label")
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

    var image = chart.selectAll(".device_icon")
        .attr("xlink:href", icon)
        .data(nodes, node_id);

    image.enter().append("image")
        .attr("class", "device_icon")
        .attr("x", function(d) { return d.x + x_offset; })
        .attr("y", function(d) { return d.y + y_offset; })
        .attr("width", icon_width)
        .attr("height", icon_height)
        .on("mouseover", function(d){
            node_info(d);
            d3.select(this).attr("xlink:href", icon); //TODO: check why need to do this
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
        .attr("xlink:href", icon)
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

    device_labels = chart.selectAll(".device_label")
        .data(nodes, node_id)

        device_labels.enter().append("text")
        .attr("x", function(d) { return d.x + x_offset; })
        .attr("y", function(d) { return d.y + y_offset + 3; } )
        .attr("class", "device_label")
        .attr("text-anchor", "middle") 
        .attr("font-family", "helvetica") 
        .attr("font-size", "small") 

        //TODO: use a general accessor for x/y of nodes
        device_labels 
        .attr("dx", icon_width/2) // padding-right
        .attr("dy", icon_height + 3) // vertical-align: middle
        .text(device_label);

    device_labels.transition()
        .attr("x", function(d) { return d.x + x_offset; })
        .attr("y", function(d) { return d.y + y_offset + 3; })
        .duration(500)

        device_labels.exit().transition()
        .duration(1000)
        .style("opacity",0)
        .remove();
    //});

        }

function redraw_paths() {

    var traceroute_line = d3.svg.line()
        .x(path_x)
        .y(path_y)
        .interpolate("cardinal")
        .tension(0.7)
        ;

    //TODO: paths need to be updated when graph changes... or perhaps fade out as no longer relevant if topology changes?
    //TODO: set paths using css and transition style rather than all the attributes hard coded

    path2 = chart.selectAll(".trace_path")
        .data(pathinfo)

        path2.enter().append("svg:path")
        .attr("d", traceroute_line)
        .attr("class", "trace_path")
        .style("stroke-width", 8)
        .style("stroke", "green")
        .style("fill", "none")
        //TODO: can use following to map to marker type
        //.attr("marker-end", function(d) { return "url(#" + d.type + ")"; });
        //.attr("marker-end", "url(#trace)")
        .on("mouseover", function(d){
            d3.select(this).style("stroke", "blue");
            d3.select(this).style("stroke-width", "6");
            path_info(d);
        })
    .on("mouseout", function(){
        d3.select(this).style("stroke-width", "3");
        d3.select(this).style("stroke", "orange");
        clear_label();
    })
    .transition()
        .duration(1000)
        .style("stroke-width", 3)
        //.style("stroke", "rgb(0,154,138)")
        .style("stroke", "orange")
        .style("opacity", 50)
        ;


}


