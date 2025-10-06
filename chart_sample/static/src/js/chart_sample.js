/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { getColor } from "@web/core/colors/colors";

const actionRegistry = registry.category("actions");



export class ChartjsSample extends Component {
    setup() {
        this.orm = useService('orm');
        this.action = useService("action");
        this.data = useState([]);
        this.filterType = useState({ value: "sale" });
        this.startDate = useState({ value: this.getCurrentMonthStart() });
        this.endDate = useState({ value: this.getCurrentMonthEnd() });
        this.searchQuery = useState({ value: "" });
        this.stats = useState({
            totalSales: 0,
            totalQuotations: 0,
            totalOrders: 0,
            totalRevenue: 0,
            salesPercent: 0,
            quotationsPercent: 0,
            ordersPercent: 0,
            revenuePercent: 0,
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
        this.goToSalesPage = this.goToSalesPage.bind(this);
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

        this.data = await this.orm.searchRead("sale.order.line", domain, ["product_id", "order_id", "price_total"]);
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

        const totalSales = await this.orm.searchRead("sale.order", domain, ["amount_total"]);
        const totalQuotations = await this.orm.searchRead("sale.order", [...domain, ['state', 'in', ['draft', 'sent', 'to_approve', 'approved']]], ["amount_total"]);
        const totalOrders = await this.orm.searchRead("sale.order", [...domain, ['state', 'in', ['sale', 'done']]], ["amount_total"]);
        const totalRevenue = await this.orm.searchRead("sale.order", [...domain, ['state', '=', 'sale']], ["amount_total"]);

        const totalSalesAmount = totalSales.reduce((sum, order) => sum + order.amount_total, 0);
        const totalQuotationsAmount = totalQuotations.reduce((sum, order) => sum + order.amount_total, 0);
        const totalOrdersAmount = totalOrders.reduce((sum, order) => sum + order.amount_total, 0);
        const totalRevenueAmount = new Intl.NumberFormat('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(totalRevenue.reduce((sum, order) => sum + order.amount_total, 0));

        this.stats.totalSales = totalSales.length;
        this.stats.totalQuotations = totalQuotations.length;
        this.stats.totalOrders = totalOrders.length;
        this.stats.totalRevenue = totalRevenueAmount;

        this.stats.salesPercent = totalRevenueAmount ? (totalSalesAmount / totalRevenueAmount) * 100 : 0;
        this.stats.quotationsPercent = totalRevenueAmount ? (totalQuotationsAmount / totalRevenueAmount) * 100 : 0;
        this.stats.ordersPercent = totalRevenueAmount ? (totalOrdersAmount / totalRevenueAmount) * 100 : 0;
        this.stats.revenuePercent = 100;
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
                    {
                        label: 'Top Orders',
                        data: data,
                        backgroundColor: color,
                    },
                ],
            },
        });

        const productLabels = this.data.map(item => item.product_id[1] || "Unknown Product");
        this.charttwo = new Chart(this.canvasReftwo.el, {
            type: "pie",
            data: {
                labels: productLabels,
                datasets: [
                    {
                        label: 'Top Products',
                        data: data,
                        backgroundColor: color,
                    },
                ],
            },
        });

        this.chartthree = new Chart(this.canvasRefthree.el, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Top Sales Orders',
                        data: data,
                        backgroundColor: color,
                        borderColor: color,
                        fill: false,
                    },
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

    goToSalesPage(filter) {
     

        const domain = [];
        if (this.startDate.value != "") {
            domain.push(['create_date', '>=', this.startDate.value]);
        }
        if (this.endDate.value != "") {
            domain.push(['create_date', '<=', this.endDate.value]);
        }

        if (filter === "sale") {
            domain.push(["state", "in", ["draft", "sent", "to_approve", "approved","sale"]]);
        } else if (filter === "quotation") {
            domain.push(["state", "in", ["draft", "sent", "to_approve", "approved"]]);
        } else if (filter === "order") {
            domain.push(["state", "in", ["sale", "done"]]);
        } else if (filter === "all") {
            domain.push(["state", "=", "sale"]);
        }

        if (this.action) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "sale.order",
                view_mode: "tree",
                views: [[false, "tree"]],
                target: "current",
                domain: domain,
            });
        } else {
            console.error("Action service is not available.");
        }
    }
}

ChartjsSample.template = "chart_sample.chartjs_sample";
actionRegistry.add("chartjs_sample", ChartjsSample);