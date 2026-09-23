app_name = "ekyc_india"
app_title = "eKYC India"
app_publisher = "hello@frappe.io"
app_description = "Indian compliance integrations"
app_email = "hello@frappe.io"
app_license = "mit"
app_logo_url = "/assets/ekyc_india/images/ekyc_india.svg"

# Apps
# ------------------

add_to_apps_screen = [
	{
		"name": "ekyc_india",
		"logo": "/assets/ekyc_india/images/ekyc_india.svg",
		"title": "eKYC India",
		"route": "/app/ekyc-india",
	}
]

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ekyc_india",
# 		"logo": "/assets/ekyc_india/logo.png",
# 		"title": "Ekyc India",
# 		"route": "/ekyc_india",
# 		"has_permission": "ekyc_india.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ekyc_india/css/ekyc_india.css"
# app_include_js = "/assets/ekyc_india/js/ekyc_india.js"

# include js, css files in header of web template
# web_include_css = "/assets/ekyc_india/css/ekyc_india.css"
# web_include_js = "/assets/ekyc_india/js/ekyc_india.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ekyc_india/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ekyc_india/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ekyc_india.utils.jinja_methods",
# 	"filters": "ekyc_india.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ekyc_india.install.before_install"
after_install = "ekyc_india.install.after_install"

# Uninstallation
# ------------

before_uninstall = "ekyc_india.uninstall.before_uninstall"
# after_uninstall = "ekyc_india.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ekyc_india.utils.before_app_install"
after_app_install = "ekyc_india.install.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ekyc_india.utils.before_app_uninstall"
# after_app_uninstall = "ekyc_india.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ekyc_india.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Loan Application": {
		"before_save": "ekyc_india.kfs.loan_application_before_save",
	}
}

# JS for the Generate KFS button on Loan Application.
doctype_js = {"Loan Application": "public/js/loan_application.js"}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ekyc_india.tasks.all"
# 	],
# 	"daily": [
# 		"ekyc_india.tasks.daily"
# 	],
# 	"hourly": [
# 		"ekyc_india.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ekyc_india.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ekyc_india.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ekyc_india.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "ekyc_india.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ekyc_india.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ekyc_india.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ekyc_india.utils.before_request"]
# after_request = ["ekyc_india.utils.after_request"]

# Job Events
# ----------
# before_job = ["ekyc_india.utils.before_job"]
# after_job = ["ekyc_india.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ekyc_india.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

workflow_methods = [
	{
		"name": "Make eSignature Request",
		"method": "ekyc_india.ekyc_india.doctype.digio_settings.digio_settings.make_esignature_request",
	},
	{
		"name": "Send eKYC Request",
		"method": "ekyc_india.ekyc_india.doctype.digio_settings.digio_settings.make_ekyc_request",
	},
]

# Fixtures
# --------
# Custom fields are created via create_kfs_custom_fields() (see install.py /
# patches/add_kfs_custom_fields.py); only the KFS print format ships as a fixture.
fixtures = [
	{
		"dt": "Print Format",
		"filters": [["name", "=", "Key Facts Statement"]],
	},
]
