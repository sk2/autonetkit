function formatNodeLocations(topology, exitAnglesByNode) {

    _.each(topology.nodes, function (node) {
        let occupied = new Set()
        _.each(exitAnglesByNode[node.id], function (angle) {
            if (angle < 1 * Math.PI / 8 && angle > -1 * Math.PI / 8) {
                occupied.add("right")
            }
            if (angle > Math.PI / 4 && angle < 4 * Math.PI / 4) {
                occupied.add("bottom")
            }
            if (angle > 6 * Math.PI / 8 || angle < -6 * Math.PI / 8) {
                occupied.add("left")
            }
            if (angle > -7 * Math.PI / 8 && angle < -1 * Math.PI / 8) {
                occupied.add("top")
            }

        })

        let locations = {
            "bottom": [0, 2, "middle"],
            "top": [0, -2, "middle"],
            "left": [-1.25, 0, "end"],
            "right": [1.25, 0, "start"],
        }

        let offset = 15

        let optimal_position = _.find(["bottom", "top", "left", "right"], function (candidate) {
            if (!occupied.has(candidate)) {
                // use this position
                return true
            }
        })
        //fallback: bottom
        if (optimal_position === undefined) {
            optimal_position = "bottom"
        }

        //and apply
        node.label_position = {
            "x": locations[optimal_position][0] * offset,
            "y": locations[optimal_position][1] * offset,
            "textAnchor": locations[optimal_position][2]
        }
    })
}

function render(topology, div, svg) {
    let xOffset = 80
    let yOffset = 40
    let linksByNode = {}
    let exitAnglesByNode = {}

    _.each(topology.nodes, function (node, id) {
        node.x = node.x + xOffset
        node.y = node.y + yOffset
        node.id = id
        linksByNode[id] = []
        exitAnglesByNode[id] = []
    })

    let renderPorts = []

    _.each(topology.ports, function (port, id) {
        port.id = id
    })


    _.each(topology.links, function (link, id) {
        let n1 = topology.nodes[link.n1]
        let n2 = topology.nodes[link.n2]

        linksByNode[link.n1].push(link.id)
        linksByNode[link.n2].push(link.id)

        link.location = {
            x1: n1.x,
            y1: n1.y,
            x2: n2.x,
            y2: n2.y,
        }

        link.id = id

        // set out the interfaces on the link
        let p1 = {}
        p1.id = link.p1
        let p2 = {}
        p2.id = link.p2
        let radius = 30

        let theta = Math.atan2((n2.y - n1.y), (n2.x - n1.x))
        p1.location = {}
        p1.location.x = n1.x + radius * Math.cos(theta)
        p1.location.y = n1.y + radius * Math.sin(theta)
        exitAnglesByNode[n1.id].push(theta)

        theta = Math.atan2((n1.y - n2.y), (n1.x - n2.x))
        p2.location = {}
        p2.location.x = n2.x + radius * Math.cos(theta)
        p2.location.y = n2.y + radius * Math.sin(theta)
        exitAnglesByNode[n2.id].push(theta)

        renderPorts.push(p1)
        renderPorts.push(p2)

    })
    formatNodeLocations(topology, exitAnglesByNode);


    function showTooltip(html, event) {
        div.transition()
            .style("opacity", .9);
        div.html(html)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px");
    }

    function hideTooltip() {
        div.transition()
            .style("opacity", 0);
    }

    function formatTooltipNode(d) {
        let exclude = ["id", "x", "y", "lo0_id", "label_position"]

        let keys = _.difference(_.keys(d), exclude)
        let html = "<table>"

        _.each(keys, function (key) {
            let val = d[key]
            html += "<tr><th>" + key + "</th><td>" + val + "</td></tr>"
        })

        html += "</table>"
        return html

    }

    function formatTooltipLink(d) {
        let exclude = ["id", "n1", "n2", "p1", "p2", "location"]

        let html = "</h3>"
        let p1Label = topology.ports[d.p1].label;
        if (p1Label) {
            html += p1Label + "."
        }
        html += topology.nodes[d.n1].label
        html += " - "
        let p2Label = topology.ports[d.p2].label;
        if (p2Label) {
            html += p2Label + "."
        }
        html += topology.nodes[d.n2].label
        html += "</h3>"

        let keys = _.difference(_.keys(d), exclude)
        html += "<table>"

        _.each(keys, function (key) {
            let val = d[key]
            html += "<tr><th>" + key + "</th><td>" + val + "</td></tr>"
        })

        html += "</table>"
        return html

    }

    function formatTooltipPort(d) {
        let exclude = ["id", "node"]

        let keys = _.difference(_.keys(d), exclude)
        let html = "<table>"

        _.each(keys, function (key) {
            let val = d[key]
            html += "<tr><th>" + key + "</th><td>" + val + "</td></tr>"
        })

        html += "</table>"
        return html

    }

    svg
        .select("#links")
        .selectAll("line")
        .data(Object.values(topology.links), d => d.id)
        .join('line')
        .attr("x1", d => {
            return d.location.x1
        })
        .attr("y1", d => {
            return d.location.y1
        })
        .attr("x2", d => {
            return d.location.x2
        })
        .attr("y2", d => {
            return d.location.y2
        })
        .on("mouseover", function (event, d) {
            let html = formatTooltipLink(d)
            showTooltip(html, event);
        })
        .on("mouseout", function () {
            hideTooltip();
        });

    svg
        .select("#nodes")
        .selectAll("circle")
        .data(Object.values(topology.nodes), d => d.id)
        .join("circle")
        .attr("r", 12)
        .attr("cx", d => d.x)
        .attr("cy", d => d.y)
        .on("mouseover", function (event, d) {

            let html = formatTooltipNode(d)
            if ("lo0_id" in d) {
                //also display loopback0 information
                html += "<hr />"
                html += formatTooltipPort(topology.ports[d.lo0_id])
            }

            showTooltip(html, event);
        })
        .on("mouseout", function () {
            hideTooltip();
        });

    svg
        .select("#nodes")
        .selectAll("text")
        .data(Object.values(topology.nodes), d => d.id)
        .join("text")
        .attr("x", d => d.x)
        .attr("y", d => d.y)
        .attr("dx", d => d.label_position.x)
        .attr("dy", d => d.label_position.y)
        .style("text-anchor", d => d.label_position.textAnchor)
        .text(d => {
            return d.label
        })


    svg
        .select("#ports")
        .selectAll("circle")
        .data(renderPorts, d => d.id)
        .join("circle")
        .attr("cx", d => d.location.x)
        .attr("cy", d => d.location.y)
        .attr("r", 6)
        .on("mouseover", function (event, d) {
            let port = topology.ports[d.id]
            let html = formatTooltipPort(port)
            showTooltip(html, event);
        })
        .on("mouseout", function () {
            hideTooltip();
        });

    let displayPorts = false

    if (displayPorts) {
        svg
            .select("#ports")
            .selectAll("text")
            .data(renderPorts, d => d.id)
            .join("text")
            .attr("x", d => {
                return d.location.x - 10
            })
            .attr("y", d => {
                return d.location.y + 20
            })
            .text(d => {
                return topology.ports[d.id].label
            })
    }

}
