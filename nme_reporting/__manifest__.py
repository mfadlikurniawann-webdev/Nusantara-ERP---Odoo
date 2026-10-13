{
    "name": "Nusantara ERP - Reporting",
    "summary": "Dashboard, sales/purchase/stock analysis, Excel export and aging PDF",
    "version": "20.0.1.0.0",
    "category": "Nusantara ERP",
    "author": "M. Fadli Kurniawan",
    "website": "https://github.com/mfadlikurniawann-webdev/Nusantara-ERP---Odoo",
    "license": "LGPL-3",
    "depends": ["nme_invoicing", "web"],
    "data": [
        "security/ir.access.csv",
        "report/nme_aging_reports.xml",
        "report/nme_aging_templates.xml",
        "views/nme_sale_report_views.xml",
        "views/nme_purchase_report_views.xml",
        "views/nme_stock_report_views.xml",
        "views/nme_dashboard_views.xml",
        "wizard/nme_report_export_views.xml",
        "views/nme_reporting_menus.xml",
    ],
    "demo": [
        "demo/nme_sale_order_history_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "nme_reporting/static/src/**/*.js",
            "nme_reporting/static/src/**/*.xml",
            "nme_reporting/static/src/**/*.scss",
        ],
        "web.assets_unit_tests": [
            "nme_reporting/static/tests/**/*",
        ],
    },
}
