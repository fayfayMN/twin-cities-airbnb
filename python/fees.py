"""
Airbnb host-only fee math for the pricing tool.

MODEL: "simplified pricing" / host-only service fee. The host absorbs the full
service fee (default 15.5% — VERIFY on your own Airbnb payout settings, it varies
by region/listing). The guest pays one all-in price; there is no separate guest
service fee under this model.

What the service fee applies to: the booking SUBTOTAL = accommodation +
cleaning fee + extra-guest/pet fees. It does NOT apply to taxes.

Taxes (e.g. Minnesota state sales tax + local lodging tax) are collected from the
guest and remitted by Airbnb — a pass-through that does not change your net
PAYOUT. (You still owe income tax on your earnings; that's outside this calc.)

All functions are pure and unit-tested at the bottom (`python fees.py`).
"""
from dataclasses import dataclass

DEFAULT_FEE_RATE = 0.155   # host-only service fee; override with your real number


@dataclass
class Payout:
    subtotal: float          # accommodation + cleaning + extras (pre-fee)
    service_fee: float       # what Airbnb keeps
    net_payout: float        # what lands in your account
    effective_rate: float    # service_fee / subtotal


def per_booking_payout(nightly, nights, cleaning=0.0, extra=0.0,
                       fee_rate=DEFAULT_FEE_RATE) -> Payout:
    """Net payout for a single booking under the host-only fee model."""
    subtotal = nightly * nights + cleaning + extra
    fee = subtotal * fee_rate
    return Payout(subtotal, fee, subtotal - fee,
                  fee / subtotal if subtotal else 0.0)


def gross_up_nightly(target_net_nightly, fee_rate=DEFAULT_FEE_RATE) -> float:
    """List price needed so the nightly portion nets `target_net_nightly`.
    To keep $100/night after a 15.5% fee, list at 100/(1-0.155) = $118.34."""
    return target_net_nightly / (1 - fee_rate)


def annual_net(nightly, booked_nights, avg_stay=3.0, cleaning=0.0,
               fee_rate=DEFAULT_FEE_RATE, operating_cost_per_night=0.0) -> dict:
    """Annualized economics.

    booked_nights: expected occupied nights per year (demand).
    avg_stay: average length of stay -> number of bookings = booked_nights/avg_stay
              (cleaning fee is charged once per booking).
    operating_cost_per_night: YOUR costs (cleaner pay, supplies, utilities) — set 0
              to see Airbnb-only net; set a value for true take-home.
    """
    bookings = booked_nights / avg_stay if avg_stay else 0
    gross_accommodation = nightly * booked_nights
    gross_cleaning = cleaning * bookings
    gross = gross_accommodation + gross_cleaning
    service_fee = gross * fee_rate
    net_payout = gross - service_fee
    operating = operating_cost_per_night * booked_nights
    take_home = net_payout - operating
    return {
        "bookings": bookings,
        "gross": gross,
        "service_fee": service_fee,
        "net_payout": net_payout,          # after Airbnb fee, before your costs
        "operating_cost": operating,
        "take_home": take_home,            # after your costs too
        "net_per_night": net_payout / booked_nights if booked_nights else 0,
    }


if __name__ == "__main__":
    # --- unit checks ---
    p = per_booking_payout(nightly=100, nights=3, cleaning=75, fee_rate=0.155)
    assert abs(p.subtotal - 375) < 1e-9
    assert abs(p.service_fee - 375 * 0.155) < 1e-9
    assert abs(p.net_payout - 375 * 0.845) < 1e-9

    assert abs(gross_up_nightly(100, 0.155) - 118.343) < 0.01

    a = annual_net(nightly=150, booked_nights=180, avg_stay=3, cleaning=75,
                   fee_rate=0.155)
    assert a["bookings"] == 60
    assert abs(a["gross"] - (150 * 180 + 75 * 60)) < 1e-6      # 27000 + 4500
    assert abs(a["net_payout"] - a["gross"] * 0.845) < 1e-6
    print("fees.py — all unit checks passed")
    print(f"  example: list $150, 180 nights, $75 cleaning ->")
    print(f"    gross ${a['gross']:,.0f}, fee ${a['service_fee']:,.0f}, "
          f"net ${a['net_payout']:,.0f} (${a['net_per_night']:,.0f}/night)")
