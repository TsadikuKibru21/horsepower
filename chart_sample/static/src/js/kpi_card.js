/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";

const actionRegistry = registry.category("actions");


export class PurchaseChart extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService("action");
        this.data = useState([]);
        this.filterType = useState({ value: "purchase" });
        this.startDate = useState({ value: this.getCurrentMonthStart() });
        this.endDate = useState({ value: this.getCurrentMonthEnd() });
        this.searchQuery = useState({ value: "" });
        this.stats = useState({
            totalPurchases: 0,
            totalRFQs: 0,
            totalOrders: 0,
            totalSpent: 0,
            purchasePercent: 0,
            rfqPercent: 0,
            ordersPercent: 0,
            spentPercent: 0,
        });

        this.canvasRef = useRef("canvas");
        this.canvasReftwo = useRef("canvastwo");
        this.canvasRefthree = useRef("canvasthree");

        onWillStart(async () => await loadJS(["/web/static/lib/Chart/Chart.js"]));

        onMounted(() => {
            this.fetchData();
            this.fetchStats();
        });

        onWillUnmount(() => {
            if (this.chart) this.chart.destroy();
            if (this.charttwo) this.charttwo.destroy();
            if (this.chartthree) this.chartthree.destroy();
        });

        // Bind methods to ensure correct context
        this.goToPurchasesPage = this.goToPurchasesPage.bind(this);
    }

    getCurrentMonthStart() {
        const date = new Date();
        return new Date(date.getFullYear(), date.getMonth(), 1).toISOString().split('T')[0];
    }

    getCurrentMonthEnd() {
        const date = new Date();
        return new Date(date.getFullYear(), date.getMonth() + 1, 0).toISOString().split('T')[0];
    }

    async fetchData() {

        const domain = [];
        if (this.startDate.value != "") {
            domain.push(['create_date', '>=', this.startDate.value]);
        }
        if (this.endDate.value != "") {
            domain.push(['create_date', '<=', this.endDate.value]);
        }
        if (this.filterType.value) {
            domain.push(['order_id.state', '=', this.filterType.value]);
        }
        
        if (this.searchQuery.value) {
            domain.push(['name', 'ilike', this.searchQuery.value]);
        }

        this.data = await this.orm.searchRead("purchase.order.line", domain, ["product_id", "order_id", "price_total"]);
        console.log('Fetched data:', this.data);
        this.renderChart();
    }

    async fetchStats() {

        const domain = [];
        if (this.startDate.value != "") {
            domain.push(['create_date', '>=', this.startDate.value]);
        }
        if (this.endDate.value != "") {
            domain.push(['create_date', '<=', this.endDate.value]);
        }
       

        const totalPurchases = await this.orm.searchRead("purchase.order", [...domain, ["state", "in", ["draft","purchase","sent","to approve"]]], ["amount_total"]);
        const totalRFQs = await this.orm.searchRead("purchase.order", [...domain, ['state', 'in', ['draft',"sent","to approve"]]], ["amount_total"]);
        const totalOrders = await this.orm.searchRead("purchase.order", [...domain, ['state', 'in', ['purchase']]], ["amount_total"]);
        const totalSpent = await this.orm.searchRead("purchase.order", [...domain, ['state', '=', 'purchase']], ["amount_total"]);

        const totalSpentAmount = totalSpent.reduce((sum, order) => sum + order.amount_total, 0);

        this.stats.totalPurchases = totalPurchases.length;
        this.stats.totalRFQs = totalRFQs.length;
        this.stats.totalOrders = totalOrders.length;
        this.stats.totalSpent = new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(totalSpentAmount);

        this.stats.purchasePercent = totalOrders.length ? (totalPurchases.length / totalOrders.length) * 100 : 0;
        this.stats.rfqPercent = totalOrders.length ? (totalRFQs.length / totalOrders.length) * 100 : 0;
        this.stats.ordersPercent = totalOrders.length ? 100 : 0;
        this.stats.spentPercent = 100;
    }

    renderChart() {
        const labels = this.data.map(item => item.order_id[1] || "Unknown Order");
        const data = this.data.map(item => item.price_total || 0);
        const color = labels.map((_, index) => getColor(index));

        if (this.chart) this.chart.destroy();
        if (this.charttwo) this.charttwo.destroy();
        if (this.chartthree) this.chartthree.destroy();

        this.chart = new Chart(this.canvasRef.el, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    { label: 'Top Purchase Orders', data: data, backgroundColor: color },
                ],
            },
        });

        const productLabels = this.data.map(item => item.product_id[1] || "Unknown Product");
        this.charttwo = new Chart(this.canvasReftwo.el, {
            type: "pie",
            data: {
                labels: productLabels,
                datasets: [
                    { label: 'Top Purchased Products', data: data, backgroundColor: color },
                ],
            },
        });

        this.chartthree = new Chart(this.canvasRefthree.el, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    { label: 'Top Purchase Orders', data: data, backgroundColor: color, borderColor: color, fill: false },
                ],
            },
        });
    }

    onStartDateChange(event) {
        this.startDate.value = event.target.value;
        this.fetchData();
        this.fetchStats();
    }

    onEndDateChange(event) {
        this.endDate.value = event.target.value;
        this.fetchData();
        this.fetchStats();
    }

    onSearchQueryChange(event) {
        this.searchQuery.value = event.target.value;
        this.fetchData();
    }

    goToPurchasesPage(filter) {

        const domain = [];
        if (this.startDate.value != "") {
            domain.push(['create_date', '>=', this.startDate.value]);
        }
        if (this.endDate.value != "") {
            domain.push(['create_date', '<=', this.endDate.value]);
        }
     
        if (filter === "purchase") {
            domain.push(["state", "in", ["draft","sent","to approve","purchase"]]);
        } else if (filter === "rfq") {
            domain.push(["state", "in", ['draft',"sent","to approve"]]);
        } else if (filter === "order") {
            domain.push(["state", "in", ["purchase"]]);
        } else if (filter === "spent") {
            domain.push(["state", "=", "purchase"]);
        }

        if (this.action) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "purchase.order",
                view_mode: "list",
                views: [[false, "list"]],
                target: "current",
                domain: domain,
            });
        } else {
            console.error("Action service is not available.");
        }
    }
}

PurchaseChart.template = "chart_sample.purchase_chart";
actionRegistry.add("purchase_chart", PurchaseChart);