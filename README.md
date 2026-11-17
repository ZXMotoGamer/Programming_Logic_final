# Programming_Logic_final

Pitstop Auto is a staff-facing Streamlit classroom demo for creating oil-change
work orders, maintaining customer records, reviewing service history, and
displaying an invoice. It uses the service and add-on prices in
[`project_layout.txt`](project_layout.txt).

## Deploy on Streamlit Community Cloud

Create an app from this GitHub repository, select the `main` branch, and set
`app.py` as the entrypoint. You do not need to install or run Streamlit on your
computer: Community Cloud reads `requirements.txt` and installs the app
dependency in its own environment.

This is a public school-project demo and must use fictional customer data only.
The app has no staff login, and records entered into a public app may be visible
to its visitors. The local JSON file is not durable cloud storage; use a hosted
database for records that must reliably survive cloud restarts or redeployments.
The app writes records to `data/customers.json` in its running environment, and
that file is ignored by Git so records are not committed to the public repository.
