var jsondata;
var socket_url = "ws://" + location.host + "/ws";
var ws = new WebSocket(socket_url);
ws.onopen = function() {
  ws.send("overlay_list");
  ws.send("overlay_id=" + overlay_id);
  ws.send("ip_allocations");
  status_label.text("WebSocket connected");
};
ws.onclose = function () {
  status_label.text("Warning: WebSocket disconnected");
};


//TODO: make "phy" default selected

var nodes_by_id = {};

var pathinfo = [];

var graph_history = [];
var ip_allocations = [];

ws.onmessage = function (evt) {
  var data = jQuery.parseJSON(evt.data);
  //TODO: parse to see if valid traceroute path or other data
  if ("graph" in data) {
    jsondata = data;
    graph_history.push(data);
    update_title();
    revision_id = graph_history.length - 1;
    propagate_revision_dropdown(graph_history); //TODO: update this with revision from webserver
    ip_allocations.children = [];
    redraw_ip_allocations();
    redraw();
  }
  else if("path" in data) {
    pathinfo.push(data['path']);
    status_label.text("Path: " + data['path']);
    redraw_paths();
  }
  else if("overlay_list" in data) {
    propagate_overlay_dropdown(data['overlay_list']);
  }
  else if("starting" in data) {
    status_label.text("Starting: " + data['starting']);
  }
  else if("lab started" in data) {
    status_label.text("Lab started on: " + data['lab started']);
  }
  else if("ip_allocations" in data) {
    ip_allocations = data['ip_allocations'];
    //jsondata = null;
    //Clear nodes and edges
    jsondata.nodes = [];
    jsondata.links = [];
    redraw();
    redraw_ip_allocations();
  }
  else {
    console.log("got data", data);
  }
}

var load_ip_allocations = function(d) {

}

function redraw_ip_allocations() {
  //adapated from http://mbostock.github.com/d3/talk/20111018/tree.html
  var diagonal = d3.svg.diagonal()
    // change x and y (for the left to right tree)
    //.projection(function(d) { return [d.y + 100, d.x]; });
    .projection(function(d) { return [d.y + 50, d.x]; });

  var layout = d3.layout.tree().size([400,400]);

  var nodes = layout.nodes(ip_allocations);

  var node = chart.selectAll("g.node")
    .data(nodes, name)
    node.enter().append("svg:g")
    .attr("transform", function(d) { return "translate(" + (d.y + 50) + "," + d.x +  ")"; })

    var nodeEnter = node.enter().append("svg:g")
    .attr("class", "node")
    .attr("transform", function(d) { return "translate(" + (d.y + 50) + "," + d.x +  ")"; });


  nodeEnter.append("svg:circle")
    .attr("r", 1e-6)
    .attr("fill", "steelblue");


  var nodeUpdate = node.transition()
    .duration(500)
    .attr("transform", function(d) { return "translate(" + (d.y + 50) + "," + d.x + ")"; });

  //TODO: fix issue with node names

  nodeUpdate.select("circle")
    .attr("r", 6);

  // Add the dot at every node
  var nodeExit = node.exit().transition()
    .duration(500)
    .attr("transform", function(d) { return "translate(" + (d.y + 50) + "," + d.x + ")"; })
    .remove();

  nodeExit.select("circle")
    .attr("r", 1e-6);

  nodeEnter.append("svg:text")
    .attr("x", function(d) { return d.children || d._children ? -10 : 10; }) 
    .attr("dy", ".3em")
    .attr("text-anchor", function(d) { return d.children || d._children ? "end" : "start"; }) //left if children otherwise right
    .attr("font-family", "helvetica") 
    .attr("font-size", "small") 
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
    .remove();
}

var propagate_overlay_dropdown = function(d) {
  d.push('ip_allocations');
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
  revision_dropdown
    .selectAll("option")
    .data(revisions)
    .enter().append("option")
    .attr("value", String)
    .text(String);

  $("#revision_select option[value=" + revision_id + "]").attr("selected", "selected")
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
    status_label.text("");
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
  return nodes[d.source].x + x_offset + 32;
}
var source_y = function(d) {
  return nodes[d.source].y  + y_offset+ 32;
}

var target_x = function(d) {
  return nodes[d.target].x + x_offset + 32;
}
var target_y = function(d) {
  return nodes[d.target].y  + y_offset+ 32;
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

var overlay_dropdown = d3.select("#overlay_select").on("change", function() {
  overlay_id = this.value;
  if (overlay_id == "ip_allocations") {
    ws.send("ip_allocations");
  }
  else {
    ws.send("overlay_id=" + overlay_id);
  }
  update_title();
  clear_graph_history();
  if (overlay_id == "nidb") {
    group_attr = "host";
    redraw(); //TODO: see if can cut this and make group auto update
  }
  else {
    group_attr = "asn";
  }
});

var update_title = function() {
  document.title = "AutoNetkit - " + overlay_id + " r" + revision_id;
}

var clear_graph_history = function() {
  graph_history = [];
  propagate_revision_dropdown(graph_history); //TODO: update this with revision from webserver
}


//TODO: replace all 32 magic numbers with icon_offset
var icon_offset = 32;

var x_offset = 10;
var y_offset = 30;

// based on http://bl.ocks.org/2920551
var fill = d3.scale.category10();



var groupFill = function(d, i) { return fill(i); };
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
    d3.geom.hull(d.values.map(function(i) { return [i.x + x_offset + 32, i.y + y_offset + 32]; }))
    .join("L")
    + "Z";
  return retval;
}

var path_x = function(d) {
  node = nodes_by_id[d];
  //return nodes[index].x + 32;
  return node.x+ 32 + x_offset;
}

var path_y = function(d) {
  node = nodes_by_id[d];
  //return nodes[index].y+ 32;
  return node.y+ 32 + y_offset;
}

var node_info = function(d) {
  //TODO: append ul/li like table example on http://christopheviau.com/d3_tutorial/
  text = d.id;
  for (attr in d) {
    if (typeof d[attr] == 'object' && d[attr] != null) {
      text += ", " + attr + ": (";
      for (subattr in d[attr]) {
        text += ", " + subattr + ": " + d[attr][subattr];
      }
      text += ") ";
    }
    else if (d[attr] != null && d[attr] != "None" && attr != "" & attr != "" && attr != "label" && attr != "id") {
      text += ", " + attr + ": " + d[attr];
    }
  }
  status_label.text("Node: " + text);
}

var group_attr = "asn";

var group_info = function(d) {
  status_label.text("Group: " + group_attr + " " + d.key);
}

var path_info = function(d) {
  status_label.text("Path: " + d);
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
  status_label.text("Link: " + text);
}



//Markers from http://bl.ocks.org/1153292
// Used for arrow-heads
// Per-type markers, as they don't inherit styles.
chart.append("svg:defs").selectAll("marker")
.data(["link_edge"])
.enter().append("svg:marker")
.attr("id", String)
.attr("viewBox", "0 -5 10 10")
.attr("refX", 40)
.attr("refY", -5)
.attr("markerWidth", 10)
.attr("markerHeight", 10)
.attr("orient", "auto")
.append("svg:path")
.attr("d", "M0,-5L10,0L0,5");


var marker_end  = function(d) {
  if (jsondata.directed) {
    return "url(#link_edge)";
  }
  return "";
}

var graph_edge = function(d) {
  var source_x = nodes[d.source].x + x_offset + 32;
  source_y =  nodes[d.source].y + y_offset + 32;
  target_x =  nodes[d.target].x + x_offset + 32;
  target_y =  nodes[d.target].y + y_offset + 32;

  if (jsondata.directed) {
    var dx = target_x - source_x,
        dy = target_y - source_y,
        dr = Math.sqrt(dx * dx + dy * dy);
    return "M" + source_x + "," + source_y + "A" + dr + "," + dr + " 0 0,1 " + target_x + "," + target_y;
  } else {
    //TODO: look at join for here
    return  "M" + source_x + "," + source_y + "L" + target_x + "," + target_y;
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
    console.log(revision_id);
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

function redraw() {
  // create the chart here with
  // the returned data

  nodes = jsondata.nodes;
  //TODO: only update if changed
  nodes.forEach(function(node) {
      //todo: should this just be the index mapping?
      nodes_by_id[node.id] = node;
      });

  node_attr_groups = d3.nest().key(function(d) { return d[group_attr]; }).entries(nodes);
  edge_attr_groups = d3.nest().key(function(d) { return d.type; }).entries(jsondata.links);

  //TODO: make group path change/exit with node data
  groupings = chart.selectAll(".attr_group")
    .data(node_attr_groups)

    var test = 0;

  var cloud_x = function(data) {
    var mean =  d3.mean(data.values, function(d) { return d.x; });
    mean = mean - cloud_width(data)/4;
    return mean;
  }

  var cloud_y = function(data) {
    var mean =  d3.mean(data.values, function(d) { return d.y; });
    //mean = mean + cloud_height(data)/2;
    return mean;
  }

  var cloud_width = function(data) {
    var max =  d3.max(data.values, function(d) { return d.x; });
    var min =  d3.min(data.values, function(d) { return d.x; });
    return 2*(max - min);
  }

  var cloud_height = function(data) {
    var max =  d3.max(data.values, function(d) { return d.y; });
    var min =  d3.min(data.values, function(d) { return d.y; });
    return 2*(max - min);
  }

  if (test == 0) {
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
  } 
  else {
    //TODO: use following instead of d groupPath
    //.data(nodes, node_id);

    groupings.enter().append("image")
      .attr("d", groupPath)
      .attr("xlink:href", "icons/cloud.svg")
      .attr("x", cloud_x)
      .attr("y", cloud_y)
      .attr("width", cloud_width)
      .attr("height", cloud_height)
      .on("mouseover", function(d){
          group_info(d);
          })
    .on("mouseout", function(){
        clear_label();
        });
    ;

    groupings.transition()
      //TODO: put x,y etc here
      .duration(500)

  }

  groupings.exit().transition()
    .duration(1000)
    .style("opacity",0)
    .remove();

  //TODO: filter the json data x and y ranges: store in nodes, and use this for the image plotting

  var line = chart.selectAll(".link_edge")
    .data(jsondata.links, edge_id)

    //line.enter().append("line")
    line.enter().append("svg:path")
    .attr("class", "link_edge")
    .attr("d", graph_edge)
    //.attr("marker-end", marker_end)
    .style("stroke", "rgb(6,120,155)")
    .on("mouseover", function(d){
        d3.select(this).style("stroke", "orange");
        d3.select(this).style("stroke-width", "4");
        d3.select(this).attr("marker-end", "");
        link_info(d);
        })
  .on("mouseout", function(){
      d3.select(this).style("stroke-width", "1");
      d3.select(this).style("stroke", "rgb(6,120,155)");
      //d3.select(this).attr("marker-end", marker_end);
      clear_label();
      });
  line.transition()
    .duration(500)
    .attr("d", graph_edge)

    line.exit().transition()
    .duration(1000)
    .style("opacity",0)
    .remove();

  var node_id = function(d) {
    return d.label + d.network;
  }

  var image = chart.selectAll(".device_icon")
    .data(nodes, node_id);

  image.enter().append("image")
    .attr("class", "device_icon")
    .attr("x", function(d) { return d.x + x_offset; })
    .attr("y", function(d) { return d.y + y_offset; })
    .attr("width", 64)
    .attr("height", 64)
    .on("mouseover", function(d){
        node_info(d);
        d3.select(this).attr("xlink:href", icon);

        })
  .on("mouseout", function(){
      clear_label();
      });

  image
    .attr("width", 64)
    .attr("height", 64)
    .transition()
    .attr("xlink:href", icon)
    .attr("x", function(d) { return d.x + x_offset; })
    .attr("y", function(d) { return d.y + y_offset; })
    .duration(500)


    image.exit().transition()
    .duration(1000)
    .style("opacity",0)
    .remove();

  device_labels = chart.selectAll(".device_label")
    .data(nodes, node_id)

    device_labels.enter().append("text")
    .attr("x", function(d) { return d.x + x_offset; })
    .attr("y", function(d) { return d.y + y_offset; } )
    .attr("class", "device_label")
    .attr("text-anchor", "middle") 
    .attr("font-family", "helvetica") 
    .attr("font-size", "small") 

    //TODO: use a general accessor for x/y of nodes
    device_labels 
    .attr("dx", 32) // padding-right
    .attr("dy", 65) // vertical-align: middle
    .text(function (d) { return d.id; } );

  device_labels.transition()
    .attr("x", function(d) { return d.x + x_offset; })
    .attr("y", function(d) { return d.y + y_offset; })
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
    .style("stroke-width", 6)
    .style("stroke", "orange")
    .style("fill", "none")
    //TODO: can use following to map to marker type
    //.attr("marker-end", function(d) { return "url(#" + d.type + ")"; });
    //.attr("marker-end", "url(#trace)")
    .on("mouseover", function(d){
        d3.select(this).style("stroke", "orange");
        d3.select(this).style("stroke-width", "6");
        path_info(d);
        })
  .on("mouseout", function(){
      d3.select(this).style("stroke-width", "3");
      d3.select(this).style("stroke", "rgb(6,120,155)");
      clear_label();
      })
  .transition()
    .duration(1000)
    .style("stroke-width", 3)
    .style("stroke", "rgb(0,154,138)")
    .style("opacity", 50)
    ;


}


