import {Component, onWillStart, proxy} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useChart} from "@web/core/utils/chart_hook";
import {useService} from "@web/core/utils/hooks";
import {formatMonetary} from "@web/views/fields/formatters";

/**
 * Landing page of Nusantara ERP: KPI cards and the sales of the last six
 * months. All figures come from one call to `nme.dashboard`, computed with the
 * rights of the current user; clicking a card opens the matching records.
 */
export class NmeDashboard extends Component {
    static template = "nme_reporting.Dashboard";

    chart = useChart(() => this.getChartConfig());

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = proxy({data: null});
        onWillStart(async () => {
            this.state.data = await this.orm.call(
                "nme.dashboard",
                "get_dashboard_data",
                []
            );
        });
    }

    formatValue(kpi) {
        if (kpi.type === "monetary") {
            return formatMonetary(kpi.value, {currencyId: this.state.data.currency_id});
        }
        return String(kpi.value);
    }

    openKpi(kpi) {
        if (kpi.action) {
            this.action.doAction(kpi.action);
        }
    }

    getChartConfig() {
        const points = this.state.data?.sales_chart || [];
        return {
            type: "bar",
            data: {
                labels: points.map((point) => point.label),
                datasets: [
                    {
                        data: points.map((point) => point.value),
                        backgroundColor: "#1F6F78",
                        borderRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {legend: {display: false}},
                scales: {y: {beginAtZero: true}},
            },
        };
    }
}

registry.category("actions").add("nme_reporting.dashboard", NmeDashboard);
