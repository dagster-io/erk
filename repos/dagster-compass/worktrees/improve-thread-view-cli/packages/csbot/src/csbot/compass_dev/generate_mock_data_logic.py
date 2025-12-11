"""
Mock Data Generator Logic for Hooli Corporation
Generates realistic CRM datasets for accounts, opportunities, and support tickets.
"""

import csv
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cached_property
from pathlib import Path
from typing import Literal, TypeVar, cast

# Set random seed for reproducibility
random.seed(42)

RevenueSegment = Literal["SMB", "midmarket", "enterprise"]
AccountType = Literal["customer", "prospect"]
Source = Literal["inbound", "outbound"]
Region = Literal["East", "West", "International"]
DeviceType = Literal["desktop", "mobile", "tablet"]
TrafficSource = Literal["organic", "paid", "direct", "referral", "social"]
EngagementLevel = Literal["low", "medium", "high"]
Page = Literal["/", "/blog", "/pricing"]
Seniority = Literal["C-level", "VP", "Director", "Manager", "Individual Contributor"]
CallOutcome = Literal["positive", "neutral", "negative"]


@dataclass
class PartialAccount:
    account_id: str

    @cached_property
    def account_name(self) -> str:
        company_suffixes = [
            "Inc",
            "Corp",
            "LLC",
            "Ltd",
            "Co",
            "Group",
            "Solutions",
            "Systems",
            "Technologies",
            "Partners",
        ]
        company_prefixes = [
            "Tech",
            "Data",
            "Cloud",
            "Digital",
            "Smart",
            "Global",
            "Advanced",
            "Innovative",
            "Dynamic",
            "Strategic",
            "Blue",
            "Green",
            "Red",
            "Silver",
            "Golden",
            "Bright",
            "Clear",
            "Sharp",
            "Quick",
            "Fast",
            "North",
            "South",
            "East",
            "West",
            "Central",
            "Pacific",
            "Atlantic",
            "Continental",
            "International",
            "Worldwide",
        ]
        account_name = f"{random.choice(company_prefixes)} {random.choice(company_suffixes)}"
        return account_name

    @cached_property
    def region(self) -> Region:
        return weighted_random_choice({"East": 30, "West": 50, "International": 20})

    @cached_property
    def account_country(self) -> str:
        if self.region == "East":
            return "United States"
        elif self.region == "West":
            return "United States"
        else:
            return weighted_random_choice(
                {"United Kingdom": 20, "Sweden": 20, "France": 20, "Germany": 30}
            )

    @cached_property
    def account_city(self) -> str:
        cities = {
            "United States": {
                "East": {
                    "New York": 15,
                    "Boston": 5,
                    "Philadelphia": 5,
                    "Washington, D.C.": 5,
                },
                "West": {
                    "Seattle": 15,
                    "Portland": 5,
                    "San Francisco": 30,
                    "Los Angeles": 10,
                },
            },
            "United Kingdom": {
                "London": 10,
                "Manchester": 5,
                "Bristol": 5,
                "Leeds": 5,
            },
            "Sweden": {"Stockholm": 10, "Gothenburg": 5, "Malmo": 5, "Uppsala": 5},
            "France": {"Paris": 10, "Lyon": 5, "Marseille": 5, "Toulouse": 5},
            "Germany": {"Berlin": 10, "Munich": 5, "Hamburg": 5, "Frankfurt": 5},
        }
        if self.region == "International":
            return weighted_random_choice(cities[self.account_country])  # type: ignore  # Union type dict[str, dict[str, int]] not compatible with expected dict[T, int]
        else:
            return weighted_random_choice(cities[self.account_country][self.region])  # type: ignore  # Union type dict[str, int] | int not compatible with expected dict[T, int]

    @cached_property
    def industry(self) -> str:
        return weighted_random_choice(
            {
                "Technology": 50,
                "Healthcare": 10,
                "Financial Services": 30,
                "Manufacturing": 10,
                "Retail": 5,
                "Education": 5,
                "Real Estate": 5,
                "Consulting": 5,
                "Media": 5,
                "Transportation": 5,
                "Energy": 5,
                "Government": 5,
                "Non-profit": 5,
                "Legal": 5,
                "Insurance": 5,
            }
        )

    @cached_property
    def revenue_segment(self) -> RevenueSegment:
        return weighted_random_choice(
            {
                "SMB": 1,
                "midmarket": 4,
                "enterprise": 3,
            }
        )

    @cached_property
    def annual_revenue(self) -> int:
        if self.revenue_segment == "SMB":
            return random.randint(100000, 1000000)
        elif self.revenue_segment == "midmarket":
            return random.randint(1000000, 10000000)
        else:
            return random.randint(10000000, 100000000)

    @cached_property
    def number_of_employees(self) -> int:
        if self.revenue_segment == "SMB":
            return random.randint(1, 100)
        elif self.revenue_segment == "midmarket":
            return random.randint(100, 5000)
        else:
            return random.randint(5000, 50000)


OpportunityType = Literal["new business", "renewal", "upsell"]
OpportunityStage = Literal[
    "1. Preopp",
    "2. Discovery",
    "3. Evaluation",
    "4. Negotiation",
    "5. Closed Won",
    "5. Closed Lost",
]


ACCOUNT_EXECS = {
    "SMB": {
        "Jake Morgan": 3,
        "Samantha Lee": 2,
    },
    "midmarket": {
        "Carlos Rivera": 3,
        "Tina Patel": 2,
    },
    "enterprise": {
        "Brian Chen": 3,
        "Donna Moriarty": 1,
    },
}

SUPPORT_ENGINEERS = {
    "Emily Zhang": 3,
    "Nate Brooks": 2,
    "Priya Desai": 1,
}

CSMS = {
    "Sarah Brown": 3,
    "David Lee": 2,
}

WIN_RATES = {
    "Jake Morgan": 0.3,
    "Samantha Lee": 0.3,
    "Carlos Rivera": 0.25,
    "Tina Patel": 0.25,
    "Brian Chen": 0.2,
    "Donna Moriarty": 0.3,
    "Sarah Brown": 0.7,
    "David Lee": 0.8,
}


PARTNERS = {
    None: 80,
    "Medford Consulting Group": 15,
    "McDougal and Associates": 5,
}

T = TypeVar("T")


def weighted_random_choice[T](weights: dict[T, int]) -> T:
    total = sum(weights.values())
    rand = random.random() * total
    while True:
        for key, weight in weights.items():
            rand -= weight
            if rand <= 0:
                return key


START_DATE = datetime(2024, 7, 24)
END_DATE = datetime(2025, 7, 24)


def random_date_between(start: datetime, end: datetime) -> datetime:
    return start + timedelta(days=random.randint(0, (end - start).days))


def new_opp_created_date() -> datetime:
    return random_date_between(START_DATE, END_DATE)


def get_rep_for_opportunity(
    opportunity_type: OpportunityType, revenue_segment: RevenueSegment
) -> str:
    if opportunity_type == "new business":
        return weighted_random_choice(ACCOUNT_EXECS[revenue_segment])
    else:
        return weighted_random_choice(CSMS)


@dataclass
class SupportTicket:
    associated_opportunity: "Opportunity"

    @cached_property
    def title(self) -> str:
        return random.choice(
            [
                "Unable to access dashboard",
                "Feature not working as expected",
                "Error when saving data",
                "Need help with API integration",
                "Billing discrepancy",
                "Slow performance",
                "Can't export data",
                "API authentication failed",
                "User permissions issue",
                "Security vulnerability report",
                "Training session request",
                "Custom field setup",
                "Mobile app crashes",
                "Dashboard not loading",
                "Report generation failed",
                "Login page not responding",
                "Data sync issues",
                "Email notifications not working",
                "Calendar integration broken",
                "File upload failing",
                "Search function not working",
                "User interface glitches",
                "Payment processing error",
                "Account settings reset",
                "Two-factor authentication problems",
                "Data backup failed",
                "Integration timeout",
                "Webhook delivery issues",
                "SSO configuration error",
                "Role permissions incorrect",
                "Audit log missing entries",
                "Real-time updates not working",
                "Bulk import failed",
                "Custom workflow broken",
                "Email template issues",
                "Analytics dashboard empty",
                "Third-party connector error",
                "Data validation failed",
                "Scheduled report missing",
                "User invitation not sent",
                "Password reset not working",
                "API rate limit exceeded",
                "Database connection timeout",
                "Cache not updating",
                "Webhook signature invalid",
                "OAuth token expired",
                "Data migration stuck",
                "Backup restore failed",
                "Custom branding not applied",
                "Multi-language support broken",
                "Dark mode toggle issue",
            ]
        )

    @property
    def body(self) -> str:
        return random.choice(
            [
                "I'm experiencing issues logging into the platform. The login page loads but "
                "authentication fails.",
                "The new feature that was released last week isn't working as documented in the "
                "release notes.",
                "When I try to save my work, I get an error message saying the data couldn't be "
                "saved.",
                "I'm trying to integrate with your API but keep getting authentication errors.",
                "There's a discrepancy in my billing statement that I need help resolving.",
                "The application has been running very slowly for the past few days.",
                "I'm trying to export my data but the export function isn't working properly.",
                "Our API calls are failing with authentication errors despite using the correct "
                "credentials.",
                "I need help setting up user permissions for my team members.",
                "I've identified a potential security issue that needs immediate attention.",
                "We need training for our new team members on the platform features.",
                "I need help setting up custom fields for our specific use case.",
                "The mobile app keeps crashing when I try to access certain features.",
                "The dashboard isn't loading properly and shows blank sections.",
                "I'm unable to generate reports that I could create before the last update.",
                "The login page is completely unresponsive and shows a blank screen.",
                "Our data synchronization between devices has stopped working completely.",
                "Email notifications for important events are not being delivered to our team.",
                "The calendar integration with Google Calendar has stopped syncing properly.",
                "File uploads are failing with a timeout error after 30 seconds.",
                "The search functionality returns no results even for known existing data.",
                "There are visual glitches in the user interface that make it difficult to use.",
                "Payment processing is failing with a generic error message.",
                "All account settings have been reset to default values without warning.",
                "Two-factor authentication is not sending SMS codes to verified numbers.",
                "Our automated data backup process failed for the third time this week.",
                "Integration with our CRM system is timing out after 60 seconds.",
                "Webhook deliveries to our endpoint are consistently failing with 500 errors.",
                "SSO configuration with our identity provider is not working properly.",
                "Role permissions are not being applied correctly to new users.",
                "Audit log entries are missing for critical user actions from yesterday.",
                "Real-time updates in the collaboration features are not working.",
                "Bulk import of 5000 records failed with validation errors.",
                "Custom workflow rules are not triggering as configured.",
                "Email templates are not rendering correctly in different email clients.",
                "Analytics dashboard shows empty charts despite having data in the system.",
                "Third-party connector for Slack is returning authentication errors.",
                "Data validation is rejecting valid entries with false positive errors.",
                "Scheduled reports are not being generated or delivered as configured.",
                "User invitation emails are not being sent to new team members.",
                "Password reset functionality is not working for any user accounts.",
                "API rate limiting is being triggered even for normal usage patterns.",
                "Database connection is timing out during peak usage hours.",
                "Cache is not updating when data changes, showing stale information.",
                "Webhook signature verification is failing for all incoming webhooks.",
                "OAuth tokens are expiring prematurely and not refreshing properly.",
                "Data migration process has been stuck at 75% for over 24 hours.",
                "Backup restore process failed with insufficient disk space error.",
                "Custom branding elements are not appearing in the user interface.",
                "Multi-language support is broken for Spanish and French translations.",
                "Dark mode toggle is not working and always defaults to light theme.",
            ]
        )

    @cached_property
    def requester_name(self) -> str:
        return random.choice(
            [
                "John Smith",
                "Sarah Johnson",
                "Michael Brown",
                "Emily Davis",
                "David Wilson",
                "Lisa Anderson",
                "Robert Taylor",
                "Jennifer Martinez",
                "Christopher Garcia",
                "Amanda Rodriguez",
                "James Thompson",
                "Michelle White",
                "Daniel Lee",
                "Jessica Hall",
                "Matthew Allen",
                "Nicole Young",
                "Andrew King",
                "Stephanie Wright",
                "Kevin Green",
                "Rachel Scott",
                "Thomas Clark",
                "Amber Lewis",
                "Ryan Walker",
                "Hannah Hall",
                "Brandon Young",
                "Megan Allen",
                "Justin Baker",
                "Lauren Gonzalez",
                "Eric Nelson",
                "Samantha Carter",
                "Adam Mitchell",
                "Brittany Perez",
                "Gregory Roberts",
                "Victoria Turner",
                "Jonathan Phillips",
                "Natalie Campbell",
                "Steven Parker",
                "Olivia Evans",
                "Timothy Edwards",
                "Sophia Collins",
            ]
        )

    @cached_property
    def assignee_name(self) -> str:
        return weighted_random_choice(SUPPORT_ENGINEERS)

    @cached_property
    def is_open(self) -> bool:
        return random.random() < 0.3

    @cached_property
    def _end_date(self) -> datetime:
        end_date = self.associated_opportunity.closed_date
        if end_date is None:
            end_date = self.associated_opportunity.created_date + timedelta(days=30)
        return end_date

    @cached_property
    def created_date(self) -> datetime:
        return random_date_between(self.associated_opportunity.created_date, self._end_date)

    @cached_property
    def closed_date(self) -> datetime | None:
        if self.is_open:
            return None
        return random_date_between(self.created_date, self._end_date)

    @property
    def open_opportunity_arr(self) -> int:
        return self.associated_opportunity.amount_dollars

    @property
    def days_open(self) -> int:
        return (END_DATE - self.created_date).days

    @cached_property
    def first_response_date(self) -> datetime | None:
        if self.is_open:
            return None
        return random_date_between(
            self.created_date,
            self.created_date + timedelta(hours=random.randint(1, 24)),
        )

    def to_dict(self) -> dict:
        return {
            "account_id": self.associated_opportunity.account.account_id,
            "account_name": self.associated_opportunity.account.account_name,
            "title": self.title,
            "body": self.body,
            "is_open": self.is_open,
            "requester_name": self.requester_name,
            "assignee_name": self.assignee_name,
            "created_date": self.created_date.strftime("%Y-%m-%d"),
            "closed_date": self.closed_date.strftime("%Y-%m-%d") if self.closed_date else None,
            "first_response_date": self.first_response_date.strftime("%Y-%m-%d %H:%M:%S")
            if self.first_response_date
            else None,
            "days_open": self.days_open,
            "open_opportunity_arr": self.open_opportunity_arr,
        }


@dataclass
class Opportunity:
    account: PartialAccount
    opportunity_type: OpportunityType
    stage: OpportunityStage
    created_date: datetime
    owner_name: str

    @cached_property
    def support_tickets(self) -> list[SupportTicket]:
        if self.is_won:
            is_high_volume = random.random() < 0.2
            num_tickets = random.randint(10, 50) if is_high_volume else random.randint(0, 3)
        else:
            num_tickets = random.randint(0, 3)

        return [SupportTicket(associated_opportunity=self) for _ in range(num_tickets)]

    @cached_property
    def sales_calls(self) -> list["SalesCall"]:
        return SalesCall.generate_for_opportunity(self)

    def __post_init__(self):
        if self.opportunity_type == "new business":
            if self.owner_name not in ACCOUNT_EXECS[self.account.revenue_segment]:
                raise ValueError(
                    f"Owner {self.owner_name} not in {ACCOUNT_EXECS[self.account.revenue_segment]}"
                )
        else:
            if self.owner_name not in CSMS:
                raise ValueError(f"Owner {self.owner_name} not in {CSMS}")

    @cached_property
    def amount_dollars(self) -> int:
        if self.account.revenue_segment == "SMB":
            return random.randint(10000, 50000)
        elif self.account.revenue_segment == "midmarket":
            return random.randint(50000, 100000)
        else:
            return random.randint(50000, 200000)

    @cached_property
    def seats(self) -> int:
        if self.account.revenue_segment == "SMB":
            return random.randint(1, 10)
        elif self.account.revenue_segment == "midmarket":
            return random.randint(5, 50)
        else:
            return random.randint(10, 200)

    @cached_property
    def partner_name(self) -> str | None:
        return weighted_random_choice(PARTNERS)

    @cached_property
    def source(self) -> Source | None:
        if self.opportunity_type != "new business":
            return None
        else:
            return weighted_random_choice({"inbound": 70, "outbound": 30})

    @cached_property
    def discovery_date(self) -> datetime | None:
        if self.stage < "2. Discovery":
            return None
        else:
            # Moves out of preopp quickly
            return self.created_date + timedelta(days=random.randint(1, 3))

    @cached_property
    def evaluation_date(self) -> datetime | None:
        if self.stage < "3. Evaluation":
            return None
        else:
            if self.account.revenue_segment == "SMB":
                days = random.randint(1, 14)
            elif self.account.revenue_segment == "midmarket":
                days = random.randint(7, 30)
            else:
                days = random.randint(7, 90)

            return cast("datetime", self.discovery_date) + timedelta(days=days)

    @cached_property
    def negotiation_date(self) -> datetime | None:
        if self.stage < "4. Negotiation":
            return None
        else:
            if self.opportunity_type != "new business":
                days = 0
            else:
                if self.account.revenue_segment == "SMB":
                    days = random.randint(1, 7)
                elif self.account.revenue_segment == "midmarket":
                    days = random.randint(1, 14)
                else:
                    days = random.randint(7, 30)

            return cast("datetime", self.evaluation_date) + timedelta(days=days)

    @cached_property
    def closed_date(self) -> datetime | None:
        if self.stage < "5. Closed Won" or self.stage < "5. Closed Lost":
            return None
        else:
            if self.account.revenue_segment == "SMB":
                days = random.randint(1, 7)
            elif self.account.revenue_segment == "midmarket":
                days = random.randint(1, 14)
            else:
                days = random.randint(7, 30)

            return cast("datetime", self.negotiation_date) + timedelta(days=days)

    @cached_property
    def opportunity_name(self) -> str:
        return f"{self.account.account_name} - {self.created_date.year} {self.opportunity_type}"

    @property
    def is_won(self) -> bool:
        return self.stage == "5. Closed Won"

    def to_dict(self) -> dict:
        return {
            "account_id": self.account.account_id,
            "account_name": self.account.account_name,
            "opportunity_type": self.opportunity_type,
            "stage": self.stage,
            "owner_name": self.owner_name,
            "amount_dollars": self.amount_dollars,
            "seats": self.seats,
            "partner_name": self.partner_name,
            "source": self.source,
            "created_date": self.created_date,
            "discovery_date": self.discovery_date,
            "evaluation_date": self.evaluation_date,
            "negotiation_date": self.negotiation_date,
            "closed_date": self.closed_date,
            "is_won": self.is_won,
        }


@dataclass
class WebPageVisit:
    account: "Account"
    visit_date: datetime
    page: Page
    session_duration_seconds: int
    page_views: int
    bounce_rate: float
    country: str
    city: str
    device_type: DeviceType
    traffic_source: TrafficSource
    engagement_level: EngagementLevel

    @classmethod
    def generate_for_account(cls, account: "Account", num_visits: int) -> list["WebPageVisit"]:
        visits = []

        # Generate visits over the last 90 days
        start_date = END_DATE - timedelta(days=90)

        for _ in range(num_visits):
            visit_date = random_date_between(start_date, END_DATE)

            # Page distribution based on account type
            if account.account_type == "customer":
                page_weights = {"/": 60, "/blog": 30, "/pricing": 10}
            else:  # prospect
                page_weights = {"/": 40, "/blog": 20, "/pricing": 40}

            page = cast("Page", weighted_random_choice(page_weights))

            # Session duration based on engagement and page
            base_duration = {"/": 120, "/blog": 300, "/pricing": 180}[page]

            # Adjust based on account type and engagement
            if account.account_type == "customer":
                base_duration *= 1.5  # Customers spend more time

            session_duration_seconds = max(30, int(base_duration * random.uniform(0.5, 2.0)))

            # Page views correlate with session duration
            page_views = max(1, int(session_duration_seconds / 60 * random.uniform(0.5, 1.5)))

            # Bounce rate - lower for customers, higher for prospects
            base_bounce_rate = 0.3 if account.account_type == "customer" else 0.6
            bounce_rate = max(0.1, min(0.9, base_bounce_rate * random.uniform(0.7, 1.3)))

            # Use account's country/city
            country = account.partial_account.account_country
            city = account.partial_account.account_city

            # Device type - more mobile for SMB, more desktop for enterprise
            if account.partial_account.revenue_segment == "SMB":
                device_weights = {"mobile": 50, "desktop": 40, "tablet": 10}
            elif account.partial_account.revenue_segment == "midmarket":
                device_weights = {"mobile": 30, "desktop": 60, "tablet": 10}
            else:  # enterprise
                device_weights = {"mobile": 20, "desktop": 70, "tablet": 10}

            device_type = cast("DeviceType", weighted_random_choice(device_weights))

            # Traffic source - customers more likely to come direct, prospects more organic/paid
            if account.account_type == "customer":
                traffic_weights = {
                    "direct": 50,
                    "organic": 30,
                    "referral": 15,
                    "social": 5,
                }
            else:
                traffic_weights = {
                    "organic": 40,
                    "paid": 30,
                    "direct": 20,
                    "referral": 8,
                    "social": 2,
                }

            traffic_source = cast("TrafficSource", weighted_random_choice(traffic_weights))

            # Engagement level based on session duration and bounce rate
            if session_duration_seconds > 300 and bounce_rate < 0.3:
                engagement_level = cast("EngagementLevel", "high")
            elif session_duration_seconds > 120 and bounce_rate < 0.6:
                engagement_level = cast("EngagementLevel", "medium")
            else:
                engagement_level = cast("EngagementLevel", "low")

            visits.append(
                cls(
                    account=account,
                    visit_date=visit_date,
                    page=page,
                    session_duration_seconds=session_duration_seconds,
                    page_views=page_views,
                    bounce_rate=bounce_rate,
                    country=country,
                    city=city,
                    device_type=device_type,
                    traffic_source=traffic_source,
                    engagement_level=engagement_level,
                )
            )

        return visits

    def to_dict(self) -> dict:
        return {
            "account_id": self.account.partial_account.account_id,
            "account_name": self.account.partial_account.account_name,
            "page": self.page,
            "visit_date": self.visit_date.strftime("%Y-%m-%d"),
            "session_duration_seconds": self.session_duration_seconds,
            "page_views": self.page_views,
            "bounce_rate": round(self.bounce_rate, 3),
            "country": self.country,
            "city": self.city,
            "device_type": self.device_type,
            "traffic_source": self.traffic_source,
            "engagement_level": self.engagement_level,
        }


@dataclass
class SalesCall:
    opportunity: "Opportunity"
    call_date: datetime
    call_owner: str
    customer_seniority: Seniority
    notes: str
    outcome: CallOutcome

    @classmethod
    def generate_for_opportunity(cls, opportunity: "Opportunity") -> list["SalesCall"]:
        calls = []

        # Determine number of calls based on opportunity type and stage
        if opportunity.opportunity_type == "new business":
            if opportunity.stage == "1. Preopp":
                num_calls = random.randint(1, 2)
            elif opportunity.stage == "2. Discovery":
                num_calls = random.randint(2, 4)
            elif opportunity.stage == "3. Evaluation":
                num_calls = random.randint(3, 6)
            elif opportunity.stage == "4. Negotiation":
                num_calls = random.randint(2, 4)
            else:  # Closed
                num_calls = random.randint(1, 2)
        else:  # renewal/upsell
            if opportunity.stage in ["1. Preopp", "2. Discovery"]:
                num_calls = random.randint(1, 3)
            elif opportunity.stage == "3. Evaluation":
                num_calls = random.randint(2, 4)
            elif opportunity.stage == "4. Negotiation":
                num_calls = random.randint(1, 3)
            else:  # Closed
                num_calls = random.randint(1, 2)

        # Generate calls for each stage the opportunity went through
        current_date = opportunity.created_date

        # Preopp calls
        if opportunity.stage >= "1. Preopp":
            for _ in range(min(1, num_calls)):
                call_date = current_date + timedelta(days=random.randint(1, 7))
                calls.append(cls._generate_call_for_stage(opportunity, call_date, "1. Preopp"))
                current_date = call_date

        # Discovery calls
        if opportunity.stage >= "2. Discovery" and opportunity.discovery_date:
            discovery_calls = min(2, num_calls - len(calls))
            for _ in range(discovery_calls):
                call_date = cast("datetime", opportunity.discovery_date) + timedelta(
                    days=random.randint(1, 14)
                )
                calls.append(cls._generate_call_for_stage(opportunity, call_date, "2. Discovery"))
                current_date = call_date

        # Evaluation calls
        if opportunity.stage >= "3. Evaluation" and opportunity.evaluation_date:
            eval_calls = min(3, num_calls - len(calls))
            for _ in range(eval_calls):
                call_date = cast("datetime", opportunity.evaluation_date) + timedelta(
                    days=random.randint(1, 30)
                )
                calls.append(cls._generate_call_for_stage(opportunity, call_date, "3. Evaluation"))
                current_date = call_date

        # Negotiation calls
        if opportunity.stage >= "4. Negotiation" and opportunity.negotiation_date:
            neg_calls = min(2, num_calls - len(calls))
            for _ in range(neg_calls):
                call_date = cast("datetime", opportunity.negotiation_date) + timedelta(
                    days=random.randint(1, 14)
                )
                calls.append(cls._generate_call_for_stage(opportunity, call_date, "4. Negotiation"))
                current_date = call_date

        # Close calls
        if opportunity.stage in ["5. Closed Won", "5. Closed Lost"] and opportunity.closed_date:
            call_date = cast("datetime", opportunity.closed_date) - timedelta(
                days=random.randint(1, 7)
            )
            calls.append(cls._generate_call_for_stage(opportunity, call_date, opportunity.stage))

        return calls

    @classmethod
    def _generate_call_for_stage(
        cls, opportunity: "Opportunity", call_date: datetime, stage: str
    ) -> "SalesCall":
        call_owner = opportunity.owner_name

        # Seniority based on revenue segment and stage
        if opportunity.account.revenue_segment == "enterprise":
            if stage in ["4. Negotiation", "5. Closed Won", "5. Closed Lost"]:
                seniority_weights = {
                    "C-level": 40,
                    "VP": 30,
                    "Director": 20,
                    "Manager": 10,
                }
            else:
                seniority_weights = {
                    "VP": 30,
                    "Director": 40,
                    "Manager": 20,
                    "Individual Contributor": 10,
                }
        elif opportunity.account.revenue_segment == "midmarket":
            if stage in ["4. Negotiation", "5. Closed Won", "5. Closed Lost"]:
                seniority_weights = {
                    "VP": 30,
                    "Director": 40,
                    "Manager": 20,
                    "Individual Contributor": 10,
                }
            else:
                seniority_weights = {
                    "Director": 40,
                    "Manager": 40,
                    "Individual Contributor": 20,
                }
        else:  # SMB
            seniority_weights = {
                "Manager": 50,
                "Individual Contributor": 40,
                "Director": 10,
            }

        customer_seniority = cast("Seniority", weighted_random_choice(seniority_weights))

        # Generate notes based on stage and outcome
        notes = cls._generate_notes_for_stage(opportunity, stage, customer_seniority)

        # Determine outcome based on stage and final result
        if opportunity.stage in ["5. Closed Won", "5. Closed Lost"]:
            outcome = "positive" if opportunity.is_won else "negative"
        else:
            # For earlier stages, outcome should hint at final result
            if opportunity.is_won:
                outcome_weights = {"positive": 60, "neutral": 30, "negative": 10}
            else:
                outcome_weights = {"negative": 60, "neutral": 30, "positive": 10}
            outcome = cast("CallOutcome", weighted_random_choice(outcome_weights))

        return cls(
            opportunity=opportunity,
            call_date=call_date,
            call_owner=call_owner,
            customer_seniority=customer_seniority,
            notes=notes,
            outcome=outcome,
        )

    @classmethod
    def _generate_notes_for_stage(
        cls, opportunity: "Opportunity", stage: str, seniority: Seniority
    ) -> str:
        notes_templates = {
            "1. Preopp": [
                "Initial outreach to {seniority} at {company}. They're currently using "
                "{competitor} but experiencing {pain_point}. Showed interest in our {feature} "
                "capabilities.",
                "First conversation with {seniority}. They mentioned {pain_point} as their biggest "
                "challenge. Currently evaluating {competitor} and {competitor2}. Timeline: "
                "{timeline}.",
                "Intro call with {seniority}. They're looking to solve {pain_point}. Budget seems "
                "to be around {budget_range}. Competition includes {competitor}.",
            ],
            "2. Discovery": [
                "Discovery call with {seniority}. Deep dive into {pain_point}. They need "
                "{feature} and {feature2}. Current solution: {competitor}. Timeline: {timeline}. "
                "Budget: {budget_range}.",
                "Qualification call - {seniority} confirmed {pain_point} is priority. They're "
                "looking at {competitor} and {competitor2}. Our {value_prop} resonated well. Next "
                "steps: {next_steps}.",
                "Discovery session with {seniority} and team. Key pain points: {pain_point}, "
                "{pain_point2}. They're evaluating {competitor}. Our {feature} addresses their "
                "needs. Timeline: {timeline}.",
            ],
            "3. Evaluation": [
                "Technical deep dive with {seniority}. They're impressed with our {feature} and "
                "{feature2}. Concerns about {objection}. Comparing us to {competitor}. Timeline: "
                "{timeline}.",
                "Evaluation call - {seniority} wants to see {feature} in action. They're also "
                "looking at {competitor}. Pricing feedback: {pricing_feedback}. Next: "
                "{next_steps}.",
                "Product demo for {seniority}. They loved our {feature} and {value_prop}. Some "
                "concerns about {objection}. Competition: {competitor}. Timeline: {timeline}.",
            ],
            "4. Negotiation": [
                "Negotiation call with {seniority}. They want {feature} included. Pricing "
                "discussion: {pricing_feedback}. Final decision timeline: {timeline}. "
                "Competition: {competitor}.",
                "Contract discussion with {seniority}. They're pushing for {objection}. Pricing: "
                "{pricing_feedback}. Timeline: {timeline}. Still evaluating {competitor}.",
                "Final negotiation - {seniority} approved budget. Terms discussed: "
                "{pricing_feedback}. Timeline: {timeline}. We're ahead of {competitor}.",
            ],
            "5. Closed Won": [
                "Closed the deal! {seniority} signed off. They chose us over {competitor} "
                "because of our {value_prop}. Implementation timeline: {timeline}.",
                "Deal won! {seniority} was impressed with our {feature} and {value_prop}. Beat "
                "{competitor} on {competitive_advantage}. Timeline: {timeline}.",
                "Contract signed with {seniority}. They valued our {value_prop} over "
                "{competitor}. Implementation starts {timeline}.",
            ],
            "5. Closed Lost": [
                "Lost to {competitor}. {seniority} said {objection} was the deciding factor. "
                "They went with {competitor} because of {competitive_disadvantage}.",
                "Deal lost to {competitor}. {seniority} felt {objection}. They chose "
                "{competitor} for {competitive_disadvantage}. Timeline: {timeline}.",
                "Lost the deal. {seniority} decided to go with {competitor} due to {objection}. "
                "Our {competitive_disadvantage} was the issue.",
            ],
        }

        # Get template and fill in variables
        template = random.choice(notes_templates[stage])

        # Define variable mappings
        variables = {
            "company": opportunity.account.account_name,
            "seniority": seniority,
            "pain_point": random.choice(
                [
                    "data silos",
                    "manual reporting",
                    "lack of real-time insights",
                    "poor user adoption",
                    "integration challenges",
                    "scalability issues",
                    "security concerns",
                    "cost overruns",
                    "compliance requirements",
                    "performance bottlenecks",
                    "limited customization",
                ]
            ),
            "pain_point2": random.choice(
                [
                    "slow response times",
                    "difficult onboarding",
                    "limited analytics",
                    "poor mobile experience",
                    "complex workflows",
                    "inadequate support",
                    "version control issues",
                    "deployment challenges",
                ]
            ),
            "feature": random.choice(
                [
                    "real-time analytics",
                    "automated workflows",
                    "advanced reporting",
                    "API integration",
                    "custom dashboards",
                    "mobile app",
                    "AI-powered insights",
                    "enterprise security",
                    "multi-tenant architecture",
                    "cloud deployment",
                    "data visualization",
                ]
            ),
            "feature2": random.choice(
                [
                    "role-based permissions",
                    "audit logging",
                    "backup and recovery",
                    "performance monitoring",
                    "custom branding",
                    "multi-language support",
                    "SSO integration",
                    "webhook support",
                ]
            ),
            "competitor": random.choice(["Pied Piper", "Endframe", "SeeFood", "YaoNet"]),
            "competitor2": random.choice(["Pied Piper", "Endframe", "SeeFood", "YaoNet"]),
            "value_prop": random.choice(
                [
                    "ease of use",
                    "superior performance",
                    "better pricing",
                    "enterprise features",
                    "excellent support",
                    "rapid deployment",
                    "scalability",
                    "security focus",
                ]
            ),
            "objection": random.choice(
                [
                    "pricing concerns",
                    "implementation timeline",
                    "feature gaps",
                    "integration complexity",
                    "security requirements",
                    "compliance needs",
                    "vendor lock-in",
                    "support quality",
                ]
            ),
            "timeline": random.choice(
                [
                    "Q1 2025",
                    "Q2 2025",
                    "Q3 2025",
                    "Q4 2025",
                    "within 30 days",
                    "within 60 days",
                    "end of year",
                    "next quarter",
                    "immediate",
                    "3-6 months",
                ]
            ),
            "budget_range": random.choice(
                [
                    "$50K-$100K",
                    "$100K-$250K",
                    "$250K-$500K",
                    "$500K+",
                    "$25K-$50K",
                    "$10K-$25K",
                ]
            ),
            "next_steps": random.choice(
                [
                    "technical demo",
                    "pricing discussion",
                    "reference calls",
                    "proof of concept",
                    "contract review",
                    "executive presentation",
                    "security review",
                    "compliance assessment",
                ]
            ),
            "pricing_feedback": random.choice(
                [
                    "within budget",
                    "need discount",
                    "competitive pricing",
                    "too expensive",
                    "good value",
                    "need to justify ROI",
                    "reasonable for features",
                    "budget approval needed",
                ]
            ),
            "competitive_advantage": random.choice(
                [
                    "better performance",
                    "lower cost",
                    "easier implementation",
                    "superior support",
                    "more features",
                    "better security",
                    "faster deployment",
                    "flexible pricing",
                ]
            ),
            "competitive_disadvantage": random.choice(
                [
                    "higher cost",
                    "missing features",
                    "complex implementation",
                    "limited support",
                    "performance issues",
                    "security concerns",
                    "longer timeline",
                    "vendor lock-in",
                ]
            ),
        }

        # Fill template
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))

        return template

    def to_dict(self) -> dict:
        return {
            "opportunity_id": (
                f"{self.opportunity.account.account_id}-{self.opportunity.opportunity_type}-"
                f"{self.opportunity.created_date.year}"
            ),
            "account_id": self.opportunity.account.account_id,
            "account_name": self.opportunity.account.account_name,
            "call_date": self.call_date.strftime("%Y-%m-%d"),
            "call_owner": self.call_owner,
            "customer_seniority": self.customer_seniority,
            "notes": self.notes,
            "outcome": self.outcome,
            "opportunity_stage": self.opportunity.stage,
            "opportunity_type": self.opportunity.opportunity_type,
        }


@dataclass
class Account:
    partial_account: PartialAccount
    opportunities: list[Opportunity]

    @cached_property
    def web_page_visits(self) -> list[WebPageVisit]:
        # Generate realistic number of visits based on account status
        if self.account_type == "customer":
            # Active customers have more visits
            if self.has_active_contract:
                num_visits = random.randint(20, 100)
            else:
                num_visits = random.randint(5, 30)
        else:
            # Prospects have fewer visits
            if self.is_sales_working_account:
                num_visits = random.randint(10, 50)
            else:
                num_visits = random.randint(1, 15)

        return WebPageVisit.generate_for_account(self, num_visits)

    @property
    def _active_contract(self) -> Opportunity | None:
        won_opportunities = [
            opportunity
            for opportunity in self.opportunities
            if opportunity.stage == "5. Closed Won"
        ]
        won_opportunities.sort(key=lambda x: cast("datetime", x.closed_date))
        return won_opportunities[-1] if won_opportunities else None

    @property
    def _most_recent_opportunity(self) -> Opportunity | None:
        opps = list(sorted(self.opportunities, key=lambda x: x.created_date))
        if len(opps) == 0:
            return None
        return opps[-1]

    @property
    def account_type(self) -> AccountType:
        if self._active_contract is not None:
            return "customer"
        else:
            return "prospect"

    @property
    def is_sales_working_account(self) -> bool:
        return len(self.opportunities) > 0

    @property
    def account_owner_name(self) -> str | None:
        return self._most_recent_opportunity.owner_name if self._most_recent_opportunity else None

    @property
    def ARR(self) -> int:
        return self._active_contract.amount_dollars if self._active_contract else 0

    @property
    def has_active_contract(self) -> bool:
        return self._active_contract is not None

    @property
    def first_contract_start_date(self) -> datetime | None:
        return self._active_contract.closed_date if self._active_contract else None

    @property
    def last_contract_end_date(self) -> datetime | None:
        return (
            cast("datetime", self._active_contract.closed_date) + timedelta(days=365)
            if self._active_contract
            else None
        )

    @property
    def account_source(self) -> Source | None:
        return self._active_contract.source if self._active_contract else None

    @property
    def contracted_seats(self) -> int:
        return self._active_contract.seats if self._active_contract else 0

    def to_dict(self) -> dict:
        return {
            "account_id": self.partial_account.account_id,
            "account_name": self.partial_account.account_name,
            "account_country": self.partial_account.account_country,
            "account_city": self.partial_account.account_city,
            "region": self.partial_account.region,
            "industry": self.partial_account.industry,
            "annual_revenue": self.partial_account.annual_revenue,
            "number_of_employees": self.partial_account.number_of_employees,
            "account_type": self.account_type,
            "is_sales_working_account": self.is_sales_working_account,
            "account_owner_name": self.account_owner_name,
            "revenue_segment": self.partial_account.revenue_segment,
            "ARR": self.ARR,
            "has_active_contract": self.has_active_contract,
            "first_contract_start_date": self.first_contract_start_date,
            "last_contract_end_date": self.last_contract_end_date,
            "contracted_seats": self.contracted_seats,
            "account_source": self.account_source,
        }


def scenario(account: PartialAccount) -> list[Opportunity]:
    owner = get_rep_for_opportunity("new business", account.revenue_segment)
    first_opp = Opportunity(
        owner_name=owner,
        created_date=new_opp_created_date(),
        account=account,
        opportunity_type="new business",
        stage=weighted_random_choice(
            {
                "1. Preopp": 1,
                "2. Discovery": 10,
                "3. Evaluation": 5,
                "4. Negotiation": 5,
                "5. Closed Won": int(WIN_RATES[owner] * 10),
                "5. Closed Lost": int((1 - WIN_RATES[owner]) * 10),
            }
        ),
    )

    if first_opp.stage != "5. Closed Won":
        return [first_opp]

    opps = [first_opp]

    postsale_owner = get_rep_for_opportunity("upsell", account.revenue_segment)
    # 20% of the time there is a midcycle upsell
    if random.random() < 0.2:
        opps.append(
            Opportunity(
                owner_name=postsale_owner,
                created_date=cast("datetime", first_opp.closed_date)
                + timedelta(days=random.randint(60, 180)),
                account=account,
                opportunity_type="upsell",
                stage=weighted_random_choice(
                    {
                        "1. Preopp": 1,
                        "2. Discovery": 10,
                        "3. Evaluation": 5,
                        "4. Negotiation": 5,
                        "5. Closed Won": int(WIN_RATES[postsale_owner] * 10),
                        "5. Closed Lost": int((1 - WIN_RATES[postsale_owner]) * 10),
                    }
                ),
            )
        )

    # Queue up the renewal
    opps.append(
        Opportunity(
            owner_name=postsale_owner,
            created_date=cast("datetime", first_opp.closed_date) + timedelta(days=300),
            account=account,
            opportunity_type="renewal",
            stage=weighted_random_choice(
                {
                    "1. Preopp": 1,
                    "2. Discovery": 10,
                    "3. Evaluation": 5,
                    "4. Negotiation": 5,
                    "5. Closed Won": int(WIN_RATES[postsale_owner] * 10),
                    "5. Closed Lost": int((1 - WIN_RATES[postsale_owner]) * 10),
                }
            ),
        )
    )
    return opps


def create_accounts() -> list[Account]:
    # assume roughly 1/3 win rate
    num_sellers = (
        len(ACCOUNT_EXECS["SMB"])
        + len(ACCOUNT_EXECS["midmarket"])
        + len(ACCOUNT_EXECS["enterprise"])
    )
    # give them each a book of 100 accounts
    num_accounts_assigned = num_sellers * 100
    num_accounts_unassigned = num_accounts_assigned * 10

    partials = [
        PartialAccount(f"ACCT-{i}") for i in range(num_accounts_assigned + num_accounts_unassigned)
    ]
    return [
        Account(
            partial_account=partial,
            opportunities=scenario(partial) if i < num_accounts_assigned else [],
        )
        for i, partial in enumerate(partials)
    ]


def generate_mock_data_files(data_dir: Path) -> dict[str, int]:
    """
    Generate mock CRM data files and return statistics about what was created.

    Args:
        data_dir: Directory where CSV files will be written

    Returns:
        Dictionary with file names as keys and record counts as values
    """
    # Ensure output directory exists
    data_dir.mkdir(exist_ok=True)

    # Generate the account data
    accounts = create_accounts()

    # Write accounts.csv
    with open(data_dir / "accounts.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=accounts[0].to_dict().keys())
        writer.writeheader()
        for account in accounts:
            writer.writerow(account.to_dict())

    # Collect opportunities
    all_opportunities = []
    for account in accounts:
        all_opportunities.extend(account.opportunities)

    # Write opportunities.csv
    if all_opportunities:
        with open(data_dir / "opportunities.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_opportunities[0].to_dict().keys())
            writer.writeheader()
            for opportunity in all_opportunities:
                writer.writerow(opportunity.to_dict())

    # Collect sales calls
    all_sales_calls = []
    for account in accounts:
        for opportunity in account.opportunities:
            all_sales_calls.extend(opportunity.sales_calls)

    # Write sales_call_notes.csv
    if all_sales_calls:
        with open(data_dir / "sales_call_notes.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_sales_calls[0].to_dict().keys())
            writer.writeheader()
            for call in all_sales_calls:
                writer.writerow(call.to_dict())

    # Collect support tickets
    all_support_tickets = []
    for account in accounts:
        for opportunity in account.opportunities:
            all_support_tickets.extend(opportunity.support_tickets)

    # Write support_tickets.csv
    if all_support_tickets:
        with open(data_dir / "support_tickets.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_support_tickets[0].to_dict().keys())
            writer.writeheader()
            for ticket in all_support_tickets:
                writer.writerow(ticket.to_dict())

    # Collect web visits
    all_web_visits = []
    for account in accounts:
        all_web_visits.extend(account.web_page_visits)

    # Write web_traffic.csv
    if all_web_visits:
        with open(data_dir / "web_traffic.csv", "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_web_visits[0].to_dict().keys())
            writer.writeheader()
            for visit in all_web_visits:
                writer.writerow(visit.to_dict())

    # Return statistics
    return {
        "accounts.csv": len(accounts),
        "opportunities.csv": len(all_opportunities),
        "sales_call_notes.csv": len(all_sales_calls),
        "support_tickets.csv": len(all_support_tickets),
        "web_traffic.csv": len(all_web_visits),
    }
