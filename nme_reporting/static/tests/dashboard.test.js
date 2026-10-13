import {expect, test} from "@odoo/hoot";
import {defineMailModels} from "@mail/../tests/mail_test_helpers";
import {
    contains,
    mockService,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import {NmeDashboard} from "@nme_reporting/dashboard/dashboard";

// The module depends on mail: its services need the mail models.
defineMailModels();

const LOW_STOCK_ACTION = {
    type: "ir.actions.act_window",
    res_model: "nme.product",
    domain: [["is_below_min", "=", true]],
};

const DASHBOARD_DATA = {
    currency_id: false,
    kpis: [
        {
            key: "orders_to_deliver",
            label: "Orders to Deliver",
            value: 4,
            type: "integer",
        },
        {
            key: "low_stock",
            label: "Products Below Minimum",
            value: 2,
            type: "integer",
            alert: true,
            action: LOW_STOCK_ACTION,
        },
    ],
    sales_chart: null,
};

test("renders one card per KPI returned by the server", async () => {
    onRpc("nme.dashboard", "get_dashboard_data", () => DASHBOARD_DATA);
    await mountWithCleanup(NmeDashboard);
    expect(".o_nme_dashboard_kpi").toHaveCount(2);
    expect("[data-kpi='orders_to_deliver'] .o_nme_dashboard_value").toHaveText("4");
    expect("[data-kpi='low_stock']").toHaveClass("border-danger");
    // No sales access: no chart.
    expect(".o_nme_dashboard_chart").toHaveCount(0);
});

test("clicking a card opens its records", async () => {
    onRpc("nme.dashboard", "get_dashboard_data", () => DASHBOARD_DATA);
    mockService("action", {
        doAction(action) {
            expect.step(action.res_model);
        },
    });
    await mountWithCleanup(NmeDashboard);
    await contains("[data-kpi='low_stock']").click();
    expect.verifySteps(["nme.product"]);
});
