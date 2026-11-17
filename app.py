"""Staff work-order app for the Pitstop Auto classroom project."""

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st


DATA_FILE = Path(__file__).parent / "data" / "customers.json"
SERVICES = {
    "Standard oil change": Decimal("39.95"),
    "Syn-blend oil change": Decimal("54.95"),
    "Full-syn oil change": Decimal("69.95"),
}
OIL_WEIGHTS = ("10w30", "5w30", "5w20")
ADD_ONS = {
    "Air filter": Decimal("24.95"),
    "Cabin air filter": Decimal("29.95"),
    "Wiper blades": Decimal("44.00"),
    "Tire rotation": Decimal("20.00"),
    "Wheel alignment": Decimal("129.95"),
}
CUSTOMER_FIELDS = (
    "name",
    "address",
    "phone",
    "vehicle_year",
    "vehicle_make",
    "vehicle_model",
    "license_plate",
)


def format_money(value: str | Decimal) -> str:
    return f"${Decimal(value):,.2f}"


def normalize_phone(phone: str) -> str:
    return "".join(character for character in phone if character.isdigit())


def load_customers() -> dict[str, dict[str, Any]]:
    try:
        with DATA_FILE.open("r", encoding="utf-8") as data_file:
            customers = json.load(data_file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as error:
        raise ValueError(f"{DATA_FILE.name} contains invalid JSON.") from error

    if not isinstance(customers, dict):
        raise ValueError(f"{DATA_FILE.name} must contain a JSON object.")

    for phone, customer in customers.items():
        if not isinstance(phone, str) or not isinstance(customer, dict):
            raise ValueError(f"{DATA_FILE.name} contains an invalid customer record.")
        if not all(isinstance(customer.get(field), str) for field in CUSTOMER_FIELDS):
            raise ValueError(f"A customer record in {DATA_FILE.name} is incomplete.")
        if not isinstance(customer.get("history"), list):
            raise ValueError(f"A customer history in {DATA_FILE.name} is invalid.")

    return customers


def save_customers(customers: dict[str, dict[str, Any]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary_file = DATA_FILE.with_suffix(".json.tmp")
    with temporary_file.open("w", encoding="utf-8") as data_file:
        json.dump(customers, data_file, indent=2, ensure_ascii=False)
        data_file.write("\n")
    temporary_file.replace(DATA_FILE)


def show_invoice(customer: dict[str, Any], ticket: dict[str, Any]) -> None:
    st.subheader("Customer invoice")
    st.caption(f"Work order {ticket['ticket_id']} · {ticket['created_at']}")
    st.write(f"**Customer:** {customer['name']}")
    st.write(f"**Address:** {customer['address']}")
    st.write(
        "**Vehicle:** "
        f"{customer['vehicle_year']} {customer['vehicle_make']} "
        f"{customer['vehicle_model']} · Plate {customer['license_plate']}"
    )

    descriptions = [f"{ticket['service']} ({ticket['oil_weight']})"]
    amounts = [format_money(ticket["service_price"])]
    for add_on in ticket["add_ons"]:
        descriptions.append(add_on["name"])
        amounts.append(format_money(add_on["price"]))

    st.table({"Service": descriptions, "Amount": amounts})
    st.markdown(f"### Total due: {format_money(ticket['total'])}")


def render_new_work_order(customers: dict[str, dict[str, Any]]) -> None:
    st.header("Create a work order")
    customer_options = ["New customer"] + sorted(customers)
    selected_phone = st.selectbox(
        "Find an existing customer by phone, or choose New customer",
        customer_options,
        format_func=lambda phone: (
            phone
            if phone == "New customer"
            else f"{customers[phone]['name']} — {phone}"
        ),
    )
    existing_customer = (
        customers.get(selected_phone)
        if selected_phone != "New customer"
        else None
    )

    if existing_customer:
        st.info(
            f"Selected: {existing_customer['name']} · "
            f"{existing_customer['vehicle_year']} "
            f"{existing_customer['vehicle_make']} "
            f"{existing_customer['vehicle_model']}"
        )

    with st.form("work_order_form"):
        if existing_customer is None:
            st.markdown("#### Customer and vehicle")
            name = st.text_input("Customer name")
            address = st.text_input("Address")
            phone = st.text_input("Phone number")
            vehicle_year = st.text_input("Vehicle year")
            vehicle_make = st.text_input("Vehicle make")
            vehicle_model = st.text_input("Vehicle model")
            license_plate = st.text_input("License plate")
        else:
            name = existing_customer["name"]
            address = existing_customer["address"]
            phone = existing_customer["phone"]
            vehicle_year = existing_customer["vehicle_year"]
            vehicle_make = existing_customer["vehicle_make"]
            vehicle_model = existing_customer["vehicle_model"]
            license_plate = existing_customer["license_plate"]

        st.markdown("#### Requested service")
        service = st.selectbox("Oil change service", list(SERVICES))
        oil_weight = st.selectbox("Oil weight", OIL_WEIGHTS)
        selected_add_ons = st.multiselect("Add-ons", list(ADD_ONS))
        submitted = st.form_submit_button("Create work order and invoice")

    if submitted:
        customer_details = {
            "name": name.strip(),
            "address": address.strip(),
            "phone": phone.strip(),
            "vehicle_year": vehicle_year.strip(),
            "vehicle_make": vehicle_make.strip(),
            "vehicle_model": vehicle_model.strip(),
            "license_plate": license_plate.strip(),
        }
        missing_fields = [
            field.replace("_", " ")
            for field, value in customer_details.items()
            if not value
        ]
        phone_key = normalize_phone(customer_details["phone"])

        if missing_fields:
            st.error("Please complete: " + ", ".join(missing_fields) + ".")
            return
        if not 7 <= len(phone_key) <= 15:
            st.error("Enter a valid phone number with 7 to 15 digits.")
            return
        if existing_customer is None and phone_key in customers:
            st.error("That phone number is already on file. Select that customer.")
            return

        customer = existing_customer
        if customer is None:
            customer = {
                **customer_details,
                "phone": phone_key,
                "history": [],
            }

        add_on_lines = [
            {"name": add_on, "price": str(ADD_ONS[add_on])}
            for add_on in selected_add_ons
        ]
        total = SERVICES[service] + sum(
            (ADD_ONS[add_on] for add_on in selected_add_ons), Decimal("0.00")
        )
        ticket = {
            "ticket_id": f"WO-{uuid4().hex[:8].upper()}",
            "created_at": datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p"),
            "service": service,
            "service_price": str(SERVICES[service]),
            "oil_weight": oil_weight,
            "add_ons": add_on_lines,
            "total": str(total),
        }
        customer["history"].append(ticket)
        customers[phone_key] = customer

        try:
            save_customers(customers)
        except OSError as error:
            st.error(f"Could not save the work order: {error}")
            return

        st.session_state["last_invoice"] = {
            "phone": phone_key,
            "ticket_id": ticket["ticket_id"],
        }
        st.success("Work order saved to customer history.")
        show_invoice(customer, ticket)
        return

    last_invoice = st.session_state.get("last_invoice")
    if isinstance(last_invoice, dict):
        customer = customers.get(last_invoice.get("phone"))
        if customer:
            ticket = next(
                (
                    item
                    for item in customer["history"]
                    if item.get("ticket_id") == last_invoice.get("ticket_id")
                ),
                None,
            )
            if ticket:
                show_invoice(customer, ticket)


def render_customer_records(customers: dict[str, dict[str, Any]]) -> None:
    st.header("Customer records")
    if not customers:
        st.info("No customer records yet. Create a work order to add one.")
        return

    selected_phone = st.selectbox(
        "Select a customer",
        sorted(customers),
        format_func=lambda phone: f"{customers[phone]['name']} — {phone}",
    )
    customer = customers[selected_phone]

    with st.form("customer_record_form"):
        st.text_input("Customer name", value=customer["name"], key="edit_name")
        st.text_input("Address", value=customer["address"], key="edit_address")
        st.text_input("Phone number", value=customer["phone"], key="edit_phone")
        st.text_input(
            "Vehicle year", value=customer["vehicle_year"], key="edit_vehicle_year"
        )
        st.text_input(
            "Vehicle make", value=customer["vehicle_make"], key="edit_vehicle_make"
        )
        st.text_input(
            "Vehicle model", value=customer["vehicle_model"], key="edit_vehicle_model"
        )
        st.text_input(
            "License plate", value=customer["license_plate"], key="edit_license_plate"
        )
        save_record = st.form_submit_button("Save customer changes")

    if save_record:
        updated_fields = {
            "name": st.session_state["edit_name"].strip(),
            "address": st.session_state["edit_address"].strip(),
            "phone": st.session_state["edit_phone"].strip(),
            "vehicle_year": st.session_state["edit_vehicle_year"].strip(),
            "vehicle_make": st.session_state["edit_vehicle_make"].strip(),
            "vehicle_model": st.session_state["edit_vehicle_model"].strip(),
            "license_plate": st.session_state["edit_license_plate"].strip(),
        }
        if not all(updated_fields.values()):
            st.error("Please complete all customer and vehicle fields.")
            return

        new_phone = normalize_phone(updated_fields["phone"])
        if not 7 <= len(new_phone) <= 15:
            st.error("Enter a valid phone number with 7 to 15 digits.")
            return
        if new_phone != selected_phone and new_phone in customers:
            st.error("Another customer already uses that phone number.")
            return

        updated_fields["phone"] = new_phone
        customer.update(updated_fields)
        if new_phone != selected_phone:
            del customers[selected_phone]
        customers[new_phone] = customer
        try:
            save_customers(customers)
        except OSError as error:
            st.error(f"Could not save customer changes: {error}")
            return
        st.success("Customer record updated.")
        st.rerun()

    st.divider()
    confirmation_key = "customer_to_delete"
    if st.session_state.get(confirmation_key) == selected_phone:
        st.warning("Deleting this customer also deletes their service history.")
        confirm_column, cancel_column = st.columns(2)
        if confirm_column.button("Confirm delete", type="primary"):
            del customers[selected_phone]
            try:
                save_customers(customers)
            except OSError as error:
                st.error(f"Could not delete the customer record: {error}")
                return
            del st.session_state[confirmation_key]
            st.success("Customer record and history deleted.")
            st.rerun()
        if cancel_column.button("Cancel"):
            del st.session_state[confirmation_key]
            st.rerun()
    elif st.button("Delete customer record"):
        st.session_state[confirmation_key] = selected_phone
        st.rerun()


def render_service_history(customers: dict[str, dict[str, Any]]) -> None:
    st.header("Service history")
    if not customers:
        st.info("No customer records yet.")
        return

    selected_phone = st.selectbox(
        "Select a customer",
        sorted(customers),
        format_func=lambda phone: f"{customers[phone]['name']} — {phone}",
        key="history_customer",
    )
    customer = customers[selected_phone]
    history = customer["history"]
    if not history:
        st.info("No work orders are saved for this customer.")
        return

    st.caption(
        f"{customer['name']} · {customer['vehicle_year']} "
        f"{customer['vehicle_make']} {customer['vehicle_model']}"
    )
    for ticket in reversed(history):
        with st.expander(
            f"{ticket['ticket_id']} · {ticket['created_at']} · "
            f"{format_money(ticket['total'])}"
        ):
            show_invoice(customer, ticket)


def main() -> None:
    st.set_page_config(page_title="Pitstop Auto Staff Workbench", layout="wide")
    st.title("Pitstop Auto")
    st.caption("Staff work orders, customer records, and service history")
    st.warning(
        "Public classroom demo: use fictional customer information only. "
        "Anyone who can open this app may be able to see records entered here."
    )

    try:
        customers = load_customers()
    except (OSError, ValueError) as error:
        st.error(f"Could not read customer records: {error}")
        st.stop()

    with st.sidebar:
        st.subheader("Staff menu")
        page = st.radio(
            "Choose a task",
            ("New work order", "Customer records", "Service history"),
            label_visibility="collapsed",
        )
        with st.expander("Service pricing"):
            for service, price in SERVICES.items():
                st.write(f"{service}: {format_money(price)}")
            st.markdown("**Add-ons**")
            for add_on, price in ADD_ONS.items():
                st.write(f"{add_on}: {format_money(price)}")

    if page == "New work order":
        render_new_work_order(customers)
    elif page == "Customer records":
        render_customer_records(customers)
    else:
        render_service_history(customers)


if __name__ == "__main__":
    main()
