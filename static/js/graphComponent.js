class GraphComponent {
    constructor(containerId, data, options = {}) {
        this.containerId = containerId;
        this.data = data;
        this.options = options;
        this.zoomLevel = 1;
        this.isPanning = false;
        this.startX = 0;
        this.startY = 0;
        this.selectedElement = null;
        this.init();
    }

    init() {
        const container = d3.select(`#${this.containerId}`);
        this.width = container.node().clientWidth;
        this.height = container.node().clientHeight;

        this.svg = container.append("svg")
            .attr("width", this.width)
            .attr("height", this.height);

        this.minimapSvg = container.append("div")
            .attr("id", "minimap-container")
            .append("svg")
            .attr("width", 200)
            .attr("height", 150);

        this.createZoomControls(container);
        this.createMarkers();
        this.createElements();
        this.createSimulation();
        this.createMinimap();
        this.addEventListeners();
    }

    createZoomControls(container) {
        const zoomControls = container.append("div")
            .attr("id", "zoom-controls");

        zoomControls.append("button")
            .text("+")
            .on("click", () => this.zoomIn());

        zoomControls.append("button")
            .text("-")
            .on("click", () => this.zoomOut());

        zoomControls.append("button")
            .text("Reset")
            .on("click", () => this.resetZoom());
    }

    createSimulation() {
        if (!this.data.nodes || !this.data.links) {
            console.error("Nodes or links data is missing");
            return;
        }

        this.simulation = d3.forceSimulation(this.data.nodes)
            .force("link", d3.forceLink(this.data.links).id(d => d.id).distance(150))
            .force("charge", d3.forceManyBody().strength(-500))
            .force("center", d3.forceCenter(this.width / 2, this.height / 2));

        this.simulation.on("tick", () => this.ticked());
    }

    createMarkers() {
        this.svg.append("defs").append("marker")
            .attr("id", "arrow")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 15)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", "#999");
    }

    createElements() {
        if (!this.data.nodes || !this.data.links) {
            console.error("Nodes or links data is missing");
            return;
        }

        this.link = this.svg.selectAll("line")
            .data(this.data.links)
            .enter().append("line")
            .style("stroke", "#999")
            .style("stroke-width", "2px")
            .attr("marker-end", "url(#arrow)")
            .on("mouseover", (event, d) => this.highlightElement(event, d, "link"))
            .on("mouseout", (event, d) => this.unhighlightElement(event, d, "link"));

        this.linkLabels = this.svg.selectAll(".link-label")
            .data(this.data.links)
            .enter().append("text")
            .attr("class", "link-label")
            .attr("text-anchor", "middle")
            .attr("dy", -5)
            .style("font-size", "12px")
            .style("fill", "#555")
            .text(d => d.type);

        this.node = this.svg.selectAll("circle")
            .data(this.data.nodes)
            .enter().append("circle")
            .attr("r", d => this.getNodeSize(d))
            .attr("fill", d => this.getNodeColor(d))
            .on("mouseover", (event, d) => this.highlightElement(event, d, "node"))
            .on("mouseout", (event, d) => this.unhighlightElement(event, d, "node"))
            .call(d3.drag()
                .on("start", (event, d) => this.dragStarted(event, d))
                .on("drag", (event, d) => this.dragged(event, d))
                .on("end", (event, d) => this.dragEnded(event, d)));

        this.labels = this.svg.selectAll(".node-label")
            .data(this.data.nodes)
            .enter().append("text")
            .attr("class", "node-label")
            .attr("text-anchor", "middle")
            .attr("dy", ".35em")
            .style("font-size", "14px")
            .style("fill", "#fff")
            .text(d => d.properties ? d.properties.name : "")
            .on("click", (event, d) => this.showPanel(d));
    }

    createMinimap() {
        this.minimapSvg.append("g")
            .attr("transform", `scale(${0.25})`)
            .append(() => this.svg.node().cloneNode(true));

        this.viewport = this.minimapSvg.append("rect")
            .attr("class", "minimap-viewport")
            .attr("width", 200 / this.zoomLevel)
            .attr("height", 150 / this.zoomLevel)
            .attr("x", 0)
            .attr("y", 0)
            .call(d3.drag().on("drag", (event) => this.dragMinimap(event)));

        this.minimapSvg.on("click", (event) => this.clickMinimap(event));
    }

    addEventListeners() {
        this.svg.on("mousedown", (event) => this.mouseDown(event));
        this.svg.on("mousemove", (event) => this.mouseMove(event));
        this.svg.on("mouseup", (event) => this.mouseUp(event));
        this.svg.on("contextmenu", (event) => event.preventDefault());

        document.addEventListener("keydown", (event) => this.keyDown(event));
        document.addEventListener("wheel", (event) => this.wheel(event));
    }

    ticked() {
        this.link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        this.linkLabels
            .attr("x", d => (d.source.x + d.target.x) / 2)
            .attr("y", d => (d.source.y + d.target.y) / 2);

        this.node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        this.labels
            .attr("x", d => d.x)
            .attr("y", d => d.y);

        this.updateMinimap();
    }

    updateMinimap() {
        this.minimapSvg.selectAll("*").remove();
        this.minimapSvg.append("g")
            .attr("transform", `scale(${0.25})`)
            .append(() => this.svg.node().cloneNode(true));

        this.viewport = this.minimapSvg.append("rect")
            .attr("class", "minimap-viewport")
            .attr("width", 200 / this.zoomLevel)
            .attr("height", 150 / this.zoomLevel)
            .attr("x", 0)
            .attr("y", 0)
            .call(d3.drag().on("drag", (event) => this.dragMinimap(event)));
    }

    dragMinimap(event) {
        let x = Math.max(0, Math.min(event.x, 200 - this.viewport.attr("width")));
        let y = Math.max(0, Math.min(event.y, 150 - this.viewport.attr("height")));
        this.svg.attr("viewBox", `${x * this.zoomLevel} ${y * this.zoomLevel} ${this.width / this.zoomLevel} ${this.height / this.zoomLevel}`);
        this.viewport.attr("x", x).attr("y", y);
    }

    clickMinimap(event) {
        let [x, y] = d3.pointer(event);
        x = Math.max(0, Math.min(x, 200 - this.viewport.attr("width")));
        y = Math.max(0, Math.min(y, 150 - this.viewport.attr("height")));
        this.svg.attr("viewBox", `${x * this.zoomLevel} ${y * this.zoomLevel} ${this.width / this.zoomLevel} ${this.height / this.zoomLevel}`);
        this.viewport.attr("x", x).attr("y", y);
    }

    mouseDown(event) {
        if (event.button === 2) {
            this.isPanning = true;
            this.startX = event.x;
            this.startY = event.y;
            this.svg.style("cursor", "grabbing");
        }
    }

    mouseMove(event) {
        if (this.isPanning) {
            let dx = (this.startX - event.x) / this.zoomLevel;
            let dy = (this.startY - event.y) / this.zoomLevel;
            let viewBox = this.svg.attr("viewBox").split(" ").map(Number);
            this.svg.attr("viewBox", `${viewBox[0] + dx} ${viewBox[1] + dy} ${viewBox[2]} ${viewBox[3]}`);
            this.startX = event.x;
            this.startY = event.y;
        }
    }

    mouseUp(event) {
        if (event.button === 2) {
            this.isPanning = false;
            this.svg.style("cursor", "default");
        }
    }

    keyDown(event) {
        if (event.shiftKey && event.key === "+") {
            this.zoomIn();
        } else if (event.shiftKey && event.key === "-") {
            this.zoomOut();
        }
    }

    wheel(event) {
        if (event.shiftKey) {
            if (event.deltaY < 0) {
                this.zoomIn();
            } else {
                this.zoomOut();
            }
        }
    }

    zoomIn() {
        this.zoomLevel += 0.1;
        this.svg.attr("transform", `scale(${this.zoomLevel})`);
        this.updateViewport();
    }

    zoomOut() {
        this.zoomLevel -= 0.1;
        this.svg.attr("transform", `scale(${this.zoomLevel})`);
        this.updateViewport();
    }

    resetZoom() {
        this.zoomLevel = 1;
        this.svg.attr("transform", `scale(${this.zoomLevel})`);
        this.svg.attr("viewBox", `0 0 ${this.width} ${this.height}`);
        this.viewport.attr("x", 0).attr("y", 0).attr("width", 200).attr("height", 150);
    }

    updateViewport() {
        let x = parseFloat(this.viewport.attr("x"));
        let y = parseFloat(this.viewport.attr("y"));
        this.viewport.attr("width", 200 / this.zoomLevel)
            .attr("height", 150 / this.zoomLevel);
        this.svg.attr("viewBox", `${x * this.zoomLevel} ${y * this.zoomLevel} ${this.width / this.zoomLevel} ${this.height / this.zoomLevel}`);
    }

    highlightElement(event, d, type) {
        d3.select(event.target).classed("highlighted", true);
        if (type === "node") {
            this.showPanel(d);
        } else if (type === "link") {
            this.showLinkPanel(d);
        }
    }

    unhighlightElement(event, d, type) {
        d3.select(event.target).classed("highlighted", false);
    }

    showPanel(data) {
        this.selectedElement = data;
        document.getElementById("panel-title").innerText = data.properties.name;
        document.getElementById("panel-content").innerHTML = `<strong>Descrição:</strong> ${data.properties.description}`;

        let nonEditablePropertiesHTML = "";
        for (let key in data.properties) {
            nonEditablePropertiesHTML += `<p>
                <strong>${key}:</strong> ${data.properties[key]}
            </p>`;
        }

        document.getElementById("non-editable-properties").innerHTML = nonEditablePropertiesHTML;
    }

    showLinkPanel(data) {
        this.selectedElement = data;
        document.getElementById("panel-title").innerText = data.type;
        document.getElementById("panel-content").innerHTML = `<strong>Tipo:</strong> ${data.type}`;

        let nonEditablePropertiesHTML = "";
        for (let key in data.properties) {
            nonEditablePropertiesHTML += `<p>
                <strong>${key}:</strong> ${data.properties[key]}
            </p>`;
        }

        document.getElementById("non-editable-properties").innerHTML = nonEditablePropertiesHTML;
    }

    getNodeSize(d) {
        if (d.labels.includes("SystemContext")) {
            return 50;
        } else if (d.labels.includes("DigitalTwin")) {
            return 40;
        } else if (d.labels.includes("TwinProperty")) {
            return 30;
        }
        return 20;
    }

    getNodeColor(d) {
        if (d.labels.includes("SystemContext")) {
            return "#ADD8E6";
        } else if (d.labels.includes("DigitalTwin")) {
            return "#00008B";
        } else if (d.labels.includes("TwinProperty")) {
            return "#FFC0CB";
        }
        return "#007bff";
    }

    dragStarted(event, d) {
        if (!event.active) this.simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    dragEnded(event, d) {
        if (!event.active) this.simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}