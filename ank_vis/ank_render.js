        var jsondata;
        var socket_url = "ws://" + location.host + "/ws";
        var ws = new WebSocket(socket_url);
        ws.onopen = function() {
          ws.send("overlay_list");
          ws.send("overlay_id=" + overlay_id);
          status_label.text("WebSocket connected");
        };
ws.onclose = function () {
  status_label.text("Warning: WebSocket disconnected");
};


//TODO: make "phy" default selected

var nodes_by_id = {};

var pathinfo = [];

ws.onmessage = function (evt) {
  var data = jQuery.parseJSON(evt.data);
  //TODO: parse to see if valid traceroute path or other data
  if ("graph" in data) {
    jsondata = data;
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
  else {
    console.log("got data", data);
  }

}

var propagate_overlay_dropdown = function(d) {
  dropdown
    .selectAll("option")
    .data(d)
    .enter().append("option")
    .attr("value", String)
    .text(String);
}

dropdown.select("option")


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

d3.select("select").on("change", function() {
    overlay_id = this.value;
    ws.send("overlay_id=" + overlay_id);
    if (overlay_id == "nidb") {
    group_attr = "host";
    redraw(); //TODO: see if can cut this and make group auto update
    }
    else {
    group_attr = "asn";
    }
    });


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

//d3.json(
//'json/overlay/ip',
//function (jsondata) {
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
      .style("opacity", 0.1)
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
    // .data(jsondata.links)

    //TODO: see why edge_id changes sometimes even though appears the same

    //line.enter().append("line")
    line.enter().append("svg:path")
    .attr("class", "link_edge")
    .attr("d", graph_edge)
    //.attr("marker-end", marker_end)
    //.attr("x1", source_x)
    //.attr("y1", source_y)
    //.attr("x2", target_x)
    //.attr("y2", target_y)
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
    //.attr("x1", source_x)
    //.attr("y1", source_y)
    //.attr("x2", target_x)
    //.attr("y2", target_y)

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


