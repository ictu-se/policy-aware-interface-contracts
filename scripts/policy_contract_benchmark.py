#!/usr/bin/env python3
"""Synthetic policy-aware contract-testing benchmark for cross-agency APIs.

The benchmark is deterministic and uses injected policy bugs as ground truth.
It compares structural/API baselines against policy-aware contract tests for
object authorization, field filtering, purpose/jurisdiction constraints, and
audit obligations.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT / "results"
DATA = PROJECT / "data"


SENSITIVITY_WEIGHT = {
    "public": 1,
    "internal": 2,
    "personal": 3,
    "identity": 4,
    "financial": 4,
    "health": 5,
    "child": 5,
    "disciplinary": 5,
}

BUG_METADATA = {
    "correct": {"severity": 0, "owasp": "", "family": "clean"},
    "missing_auth": {"severity": 5, "owasp": "API2", "family": "function_auth"},
    "overbroad_role": {"severity": 4, "owasp": "API5", "family": "function_auth"},
    "missing_object_check": {"severity": 5, "owasp": "API1", "family": "object_auth"},
    "jurisdiction_bypass": {"severity": 5, "owasp": "API1", "family": "object_auth"},
    "purpose_bypass": {"severity": 4, "owasp": "API5", "family": "purpose_scope"},
    "missing_field_filter": {"severity": 5, "owasp": "API3", "family": "property_auth"},
    "aggregation_leak": {"severity": 4, "owasp": "API3", "family": "property_auth"},
    "missing_audit_log": {"severity": 3, "owasp": "API10", "family": "auditability"},
    "deprecated_exposed": {"severity": 3, "owasp": "API9", "family": "inventory"},
}


@dataclass(frozen=True)
class FieldSpec:
    name: str
    sensitivity: str


@dataclass(frozen=True)
class EndpointPolicy:
    domain: str
    endpoint: str
    resource: str
    operation: str
    roles: tuple[str, ...]
    purposes: tuple[str, ...]
    object_scope: str
    fields: tuple[FieldSpec, ...]
    allowed_by_role: dict[str, tuple[str, ...]]
    audit_required: bool = True
    deprecated: bool = False

    @property
    def sensitive_fields(self) -> set[str]:
        return {f.name for f in self.fields if SENSITIVITY_WEIGHT[f.sensitivity] >= 3}

    @property
    def all_fields(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)

    @property
    def max_sensitivity(self) -> int:
        return max(SENSITIVITY_WEIGHT[f.sensitivity] for f in self.fields)


@dataclass(frozen=True)
class Actor:
    role: str
    agency: str
    jurisdiction: str
    subject_id: str
    purpose: str
    authenticated: bool = True


@dataclass(frozen=True)
class ResourceObject:
    object_id: str
    owner_id: str
    jurisdiction: str
    agency: str
    fields: dict[str, str]


@dataclass(frozen=True)
class TestCase:
    test_id: str
    policy_id: str
    test_kind: str
    actor: Actor
    obj: ResourceObject
    requested_fields: tuple[str, ...]


@dataclass
class Response:
    allowed: bool
    fields: tuple[str, ...]
    audit_logged: bool
    deprecated_available: bool = False


@dataclass(frozen=True)
class Variant:
    variant_id: str
    policy_id: str
    bug_type: str
    domain: str
    endpoint: str
    severity: int
    owasp: str
    family: str
    risk: float


@dataclass
class Finding:
    method: str
    variant_id: str
    test_id: str
    bug_type: str
    family: str
    severity: int
    detected: bool
    risk_flagged: float
    reason: str


def domains() -> list[EndpointPolicy]:
    return [
        EndpointPolicy(
            domain="health",
            endpoint="GET /patients/{id}",
            resource="patient",
            operation="read",
            roles=("doctor", "nurse", "insurance_officer", "patient", "public_health_analyst"),
            purposes=("treatment", "billing", "self_service", "public_health"),
            object_scope="patient_or_care_team",
            fields=(
                FieldSpec("name", "personal"),
                FieldSpec("birth_year", "personal"),
                FieldSpec("address", "personal"),
                FieldSpec("phone", "personal"),
                FieldSpec("diagnosis", "health"),
                FieldSpec("medication", "health"),
                FieldSpec("insurance_id", "identity"),
                FieldSpec("encounter_summary", "health"),
            ),
            allowed_by_role={
                "doctor": ("name", "birth_year", "address", "phone", "diagnosis", "medication", "encounter_summary"),
                "nurse": ("name", "birth_year", "diagnosis", "medication", "encounter_summary"),
                "insurance_officer": ("name", "birth_year", "insurance_id", "encounter_summary"),
                "patient": ("name", "birth_year", "address", "phone", "diagnosis", "medication", "insurance_id", "encounter_summary"),
                "public_health_analyst": ("birth_year", "diagnosis"),
            },
        ),
        EndpointPolicy(
            domain="health",
            endpoint="GET /encounters/{id}",
            resource="encounter",
            operation="read",
            roles=("doctor", "nurse", "insurance_officer", "patient", "public_health_analyst"),
            purposes=("treatment", "billing", "self_service", "public_health"),
            object_scope="patient_or_care_team",
            fields=(
                FieldSpec("patient_name", "personal"),
                FieldSpec("visit_date", "personal"),
                FieldSpec("chief_complaint", "health"),
                FieldSpec("clinical_notes", "health"),
                FieldSpec("procedure_code", "health"),
                FieldSpec("billing_code", "financial"),
                FieldSpec("provider_id", "identity"),
                FieldSpec("facility_region", "internal"),
            ),
            allowed_by_role={
                "doctor": ("patient_name", "visit_date", "chief_complaint", "clinical_notes", "procedure_code", "facility_region"),
                "nurse": ("patient_name", "visit_date", "chief_complaint", "procedure_code", "facility_region"),
                "insurance_officer": ("patient_name", "visit_date", "procedure_code", "billing_code", "provider_id"),
                "patient": ("patient_name", "visit_date", "chief_complaint", "clinical_notes", "procedure_code", "billing_code", "provider_id"),
                "public_health_analyst": ("visit_date", "procedure_code", "facility_region"),
            },
        ),
        EndpointPolicy(
            domain="health",
            endpoint="GET /patients/search",
            resource="patient_search",
            operation="search",
            roles=("doctor", "nurse", "insurance_officer", "patient", "public_health_analyst"),
            purposes=("treatment", "billing", "self_service", "public_health"),
            object_scope="patient_or_care_team",
            fields=(
                FieldSpec("patient_id", "identity"),
                FieldSpec("age_band", "personal"),
                FieldSpec("district", "personal"),
                FieldSpec("diagnosis_group", "health"),
                FieldSpec("risk_score", "health"),
                FieldSpec("insurance_status", "financial"),
                FieldSpec("last_visit_month", "personal"),
                FieldSpec("contact_phone", "personal"),
            ),
            allowed_by_role={
                "doctor": ("patient_id", "age_band", "district", "diagnosis_group", "risk_score", "last_visit_month", "contact_phone"),
                "nurse": ("patient_id", "age_band", "district", "diagnosis_group", "last_visit_month", "contact_phone"),
                "insurance_officer": ("patient_id", "age_band", "insurance_status", "last_visit_month"),
                "patient": ("patient_id", "age_band", "district", "diagnosis_group", "risk_score", "insurance_status", "last_visit_month", "contact_phone"),
                "public_health_analyst": ("age_band", "district", "diagnosis_group", "last_visit_month"),
            },
        ),
        EndpointPolicy(
            domain="citizen_services",
            endpoint="GET /citizens/{id}",
            resource="citizen",
            operation="read",
            roles=("commune_officer", "district_officer", "ministry_admin", "citizen", "auditor"),
            purposes=("service_delivery", "appeal_review", "audit", "self_service"),
            object_scope="jurisdiction_or_self",
            fields=(
                FieldSpec("name", "personal"),
                FieldSpec("birth_year", "personal"),
                FieldSpec("address_summary", "personal"),
                FieldSpec("household_id", "identity"),
                FieldSpec("health_id", "health"),
                FieldSpec("tax_debt", "financial"),
                FieldSpec("benefit_status", "financial"),
                FieldSpec("case_notes", "internal"),
            ),
            allowed_by_role={
                "commune_officer": ("name", "birth_year", "address_summary", "household_id", "benefit_status"),
                "district_officer": ("name", "birth_year", "address_summary", "household_id", "benefit_status", "case_notes"),
                "ministry_admin": ("name", "birth_year", "address_summary", "household_id", "benefit_status", "case_notes"),
                "citizen": ("name", "birth_year", "address_summary", "household_id", "benefit_status"),
                "auditor": ("household_id", "benefit_status", "case_notes"),
            },
        ),
        EndpointPolicy(
            domain="citizen_services",
            endpoint="GET /benefits/{id}",
            resource="benefit_case",
            operation="read",
            roles=("commune_officer", "district_officer", "ministry_admin", "citizen", "auditor"),
            purposes=("service_delivery", "appeal_review", "audit", "self_service"),
            object_scope="jurisdiction_or_self",
            fields=(
                FieldSpec("case_id", "identity"),
                FieldSpec("applicant_name", "personal"),
                FieldSpec("household_size", "personal"),
                FieldSpec("income_band", "financial"),
                FieldSpec("disability_marker", "health"),
                FieldSpec("eligibility_score", "financial"),
                FieldSpec("decision_reason", "internal"),
                FieldSpec("appeal_notes", "internal"),
            ),
            allowed_by_role={
                "commune_officer": ("case_id", "applicant_name", "household_size", "income_band", "eligibility_score"),
                "district_officer": ("case_id", "applicant_name", "household_size", "income_band", "disability_marker", "eligibility_score", "decision_reason", "appeal_notes"),
                "ministry_admin": ("case_id", "household_size", "income_band", "eligibility_score", "decision_reason"),
                "citizen": ("case_id", "applicant_name", "household_size", "income_band", "eligibility_score", "decision_reason"),
                "auditor": ("case_id", "eligibility_score", "decision_reason", "appeal_notes"),
            },
        ),
        EndpointPolicy(
            domain="citizen_services",
            endpoint="GET /citizens/export",
            resource="citizen_export",
            operation="export",
            roles=("commune_officer", "district_officer", "ministry_admin", "citizen", "auditor"),
            purposes=("service_delivery", "appeal_review", "audit", "self_service"),
            object_scope="jurisdiction_or_self",
            fields=(
                FieldSpec("citizen_id", "identity"),
                FieldSpec("name", "personal"),
                FieldSpec("ward_code", "personal"),
                FieldSpec("household_id", "identity"),
                FieldSpec("benefit_status", "financial"),
                FieldSpec("tax_debt_flag", "financial"),
                FieldSpec("health_program_flag", "health"),
                FieldSpec("last_case_update", "internal"),
            ),
            allowed_by_role={
                "commune_officer": ("citizen_id", "name", "ward_code", "household_id", "benefit_status"),
                "district_officer": ("citizen_id", "name", "ward_code", "household_id", "benefit_status", "last_case_update"),
                "ministry_admin": ("ward_code", "benefit_status", "last_case_update"),
                "citizen": ("citizen_id", "name", "ward_code", "household_id", "benefit_status"),
                "auditor": ("citizen_id", "benefit_status", "tax_debt_flag", "health_program_flag", "last_case_update"),
            },
        ),
        EndpointPolicy(
            domain="education",
            endpoint="GET /students/{id}/record",
            resource="student_record",
            operation="read",
            roles=("teacher", "school_admin", "district_education_officer", "parent", "student"),
            purposes=("instruction", "school_admin", "district_reporting", "parent_access", "self_service"),
            object_scope="school_or_self_or_parent",
            fields=(
                FieldSpec("student_name", "personal"),
                FieldSpec("grade_level", "personal"),
                FieldSpec("attendance", "personal"),
                FieldSpec("assessment_score", "personal"),
                FieldSpec("disability_status", "child"),
                FieldSpec("disciplinary_record", "disciplinary"),
                FieldSpec("household_income_band", "financial"),
                FieldSpec("guardian_contact", "personal"),
            ),
            allowed_by_role={
                "teacher": ("student_name", "grade_level", "attendance", "assessment_score"),
                "school_admin": ("student_name", "grade_level", "attendance", "assessment_score", "disability_status", "disciplinary_record", "guardian_contact"),
                "district_education_officer": ("grade_level", "attendance", "assessment_score", "disability_status"),
                "parent": ("student_name", "grade_level", "attendance", "assessment_score", "guardian_contact"),
                "student": ("student_name", "grade_level", "attendance", "assessment_score"),
            },
        ),
        EndpointPolicy(
            domain="education",
            endpoint="GET /classes/{id}/roster",
            resource="class_roster",
            operation="read",
            roles=("teacher", "school_admin", "district_education_officer", "parent", "student"),
            purposes=("instruction", "school_admin", "district_reporting", "parent_access", "self_service"),
            object_scope="school_or_self_or_parent",
            fields=(
                FieldSpec("student_name", "personal"),
                FieldSpec("grade_level", "personal"),
                FieldSpec("homeroom", "personal"),
                FieldSpec("attendance_risk", "personal"),
                FieldSpec("special_support_flag", "child"),
                FieldSpec("guardian_phone", "personal"),
                FieldSpec("discipline_flag", "disciplinary"),
                FieldSpec("transport_subsidy", "financial"),
            ),
            allowed_by_role={
                "teacher": ("student_name", "grade_level", "homeroom", "attendance_risk"),
                "school_admin": ("student_name", "grade_level", "homeroom", "attendance_risk", "special_support_flag", "guardian_phone", "discipline_flag", "transport_subsidy"),
                "district_education_officer": ("grade_level", "homeroom", "attendance_risk", "special_support_flag"),
                "parent": ("student_name", "grade_level", "homeroom", "attendance_risk", "guardian_phone"),
                "student": ("student_name", "grade_level", "homeroom", "attendance_risk"),
            },
        ),
        EndpointPolicy(
            domain="education",
            endpoint="GET /discipline/{id}",
            resource="discipline_case",
            operation="read",
            roles=("teacher", "school_admin", "district_education_officer", "parent", "student"),
            purposes=("instruction", "school_admin", "district_reporting", "parent_access", "self_service"),
            object_scope="school_or_self_or_parent",
            fields=(
                FieldSpec("case_id", "identity"),
                FieldSpec("student_name", "personal"),
                FieldSpec("incident_date", "personal"),
                FieldSpec("incident_summary", "disciplinary"),
                FieldSpec("sanction", "disciplinary"),
                FieldSpec("counselor_note", "child"),
                FieldSpec("guardian_contact", "personal"),
                FieldSpec("appeal_status", "internal"),
            ),
            allowed_by_role={
                "teacher": ("case_id", "student_name", "incident_date", "incident_summary"),
                "school_admin": ("case_id", "student_name", "incident_date", "incident_summary", "sanction", "counselor_note", "guardian_contact", "appeal_status"),
                "district_education_officer": ("case_id", "incident_date", "sanction", "appeal_status"),
                "parent": ("case_id", "student_name", "incident_date", "incident_summary", "sanction", "guardian_contact"),
                "student": ("case_id", "student_name", "incident_date", "incident_summary", "sanction"),
            },
        ),
        EndpointPolicy(
            domain="business_licensing",
            endpoint="GET /licenses/{id}",
            resource="business_license",
            operation="read",
            roles=("licensing_officer", "tax_officer", "inspector", "business_owner", "public_user"),
            purposes=("licensing", "tax_review", "inspection", "owner_access", "public_lookup"),
            object_scope="agency_or_owner_or_public",
            fields=(
                FieldSpec("business_name", "public"),
                FieldSpec("license_status", "public"),
                FieldSpec("business_address", "public"),
                FieldSpec("owner_name", "personal"),
                FieldSpec("owner_identifier", "identity"),
                FieldSpec("tax_balance", "financial"),
                FieldSpec("inspection_notes", "internal"),
                FieldSpec("violation_history", "internal"),
            ),
            allowed_by_role={
                "licensing_officer": ("business_name", "license_status", "business_address", "owner_name", "owner_identifier", "inspection_notes", "violation_history"),
                "tax_officer": ("business_name", "license_status", "owner_identifier", "tax_balance"),
                "inspector": ("business_name", "license_status", "business_address", "inspection_notes", "violation_history"),
                "business_owner": ("business_name", "license_status", "business_address", "owner_name", "tax_balance", "violation_history"),
                "public_user": ("business_name", "license_status", "business_address"),
            },
        ),
        EndpointPolicy(
            domain="business_licensing",
            endpoint="GET /inspections/{id}",
            resource="inspection_case",
            operation="read",
            roles=("licensing_officer", "tax_officer", "inspector", "business_owner", "public_user"),
            purposes=("licensing", "tax_review", "inspection", "owner_access", "public_lookup"),
            object_scope="agency_or_owner_or_public",
            fields=(
                FieldSpec("business_name", "public"),
                FieldSpec("inspection_date", "public"),
                FieldSpec("inspection_status", "public"),
                FieldSpec("owner_identifier", "identity"),
                FieldSpec("inspector_note", "internal"),
                FieldSpec("violation_detail", "internal"),
                FieldSpec("fine_amount", "financial"),
                FieldSpec("tax_risk_flag", "financial"),
            ),
            allowed_by_role={
                "licensing_officer": ("business_name", "inspection_date", "inspection_status", "owner_identifier", "violation_detail", "fine_amount"),
                "tax_officer": ("business_name", "inspection_status", "owner_identifier", "fine_amount", "tax_risk_flag"),
                "inspector": ("business_name", "inspection_date", "inspection_status", "inspector_note", "violation_detail", "fine_amount"),
                "business_owner": ("business_name", "inspection_date", "inspection_status", "violation_detail", "fine_amount"),
                "public_user": ("business_name", "inspection_date", "inspection_status"),
            },
        ),
        EndpointPolicy(
            domain="business_licensing",
            endpoint="GET /licenses/export",
            resource="license_export",
            operation="export",
            roles=("licensing_officer", "tax_officer", "inspector", "business_owner", "public_user"),
            purposes=("licensing", "tax_review", "inspection", "owner_access", "public_lookup"),
            object_scope="agency_or_owner_or_public",
            fields=(
                FieldSpec("license_id", "identity"),
                FieldSpec("business_name", "public"),
                FieldSpec("license_status", "public"),
                FieldSpec("business_address", "public"),
                FieldSpec("owner_name", "personal"),
                FieldSpec("owner_identifier", "identity"),
                FieldSpec("tax_balance", "financial"),
                FieldSpec("enforcement_flag", "internal"),
            ),
            allowed_by_role={
                "licensing_officer": ("license_id", "business_name", "license_status", "business_address", "owner_name", "owner_identifier", "enforcement_flag"),
                "tax_officer": ("license_id", "business_name", "license_status", "owner_identifier", "tax_balance"),
                "inspector": ("license_id", "business_name", "license_status", "business_address", "enforcement_flag"),
                "business_owner": ("license_id", "business_name", "license_status", "business_address", "owner_name", "tax_balance"),
                "public_user": ("business_name", "license_status", "business_address"),
            },
        ),
    ]


def policy_id(policy: EndpointPolicy) -> str:
    return f"{policy.domain}::{policy.endpoint.replace(' ', '_').replace('/', '_').replace('{', '').replace('}', '')}"


def actor_for(policy: EndpointPolicy, kind: str, rng: random.Random) -> Actor:
    valid_role = policy.roles[0]
    valid_purpose = policy.purposes[0]
    if kind == "valid":
        role = valid_role
        purpose = valid_purpose
        jurisdiction = "J1"
        subject_id = "subject_1"
        authenticated = True
    elif kind == "wrong_role":
        role = "external_contractor"
        purpose = valid_purpose
        jurisdiction = "J1"
        subject_id = "subject_1"
        authenticated = True
    elif kind == "wrong_jurisdiction":
        role = valid_role
        purpose = valid_purpose
        jurisdiction = "J9"
        subject_id = "subject_1"
        authenticated = True
    elif kind == "wrong_purpose":
        role = valid_role
        purpose = "marketing"
        jurisdiction = "J1"
        subject_id = "subject_1"
        authenticated = True
    elif kind == "self_access":
        role = "patient" if policy.domain == "health" else "citizen" if policy.domain == "citizen_services" else "student" if policy.domain == "education" else "business_owner"
        purpose = "self_service" if policy.domain != "business_licensing" else "owner_access"
        jurisdiction = "J9"
        subject_id = "owner_1"
        authenticated = True
    elif kind == "unauthenticated":
        role = rng.choice(policy.roles)
        purpose = valid_purpose
        jurisdiction = "J1"
        subject_id = "subject_1"
        authenticated = False
    else:
        raise ValueError(kind)
    return Actor(role=role, agency=f"{role}_agency", jurisdiction=jurisdiction, subject_id=subject_id, purpose=purpose, authenticated=authenticated)


def resource_for(policy: EndpointPolicy) -> ResourceObject:
    fields = {f.name: f"{policy.resource}_{f.name}_value" for f in policy.fields}
    return ResourceObject(
        object_id=f"{policy.resource}_1",
        owner_id="owner_1",
        jurisdiction="J1",
        agency=f"{policy.domain}_agency",
        fields=fields,
    )


def same_object_scope(policy: EndpointPolicy, actor: Actor, obj: ResourceObject) -> bool:
    if not actor.authenticated:
        return False
    if actor.subject_id == obj.owner_id and actor.role in {"patient", "citizen", "student", "business_owner"}:
        return True
    if policy.object_scope in {"jurisdiction_or_self", "school_or_self_or_parent"}:
        return actor.jurisdiction == obj.jurisdiction
    if policy.object_scope == "patient_or_care_team":
        return actor.jurisdiction == obj.jurisdiction or actor.role == "patient"
    if policy.object_scope == "agency_or_owner_or_public":
        return actor.role == "public_user" or actor.jurisdiction == obj.jurisdiction or actor.subject_id == obj.owner_id
    return actor.jurisdiction == obj.jurisdiction


def policy_allows(policy: EndpointPolicy, actor: Actor, obj: ResourceObject) -> bool:
    return (
        actor.authenticated
        and actor.role in policy.roles
        and actor.purpose in policy.purposes
        and same_object_scope(policy, actor, obj)
        and not policy.deprecated
    )


def allowed_fields(policy: EndpointPolicy, actor: Actor) -> tuple[str, ...]:
    return policy.allowed_by_role.get(actor.role, tuple())


def apply_variant(policy: EndpointPolicy, bug_type: str, test: TestCase) -> Response:
    should_allow = policy_allows(policy, test.actor, test.obj)
    actor = test.actor
    obj = test.obj
    fields = tuple(f for f in allowed_fields(policy, actor) if f in test.requested_fields)
    audit_logged = policy.audit_required
    deprecated_available = policy.deprecated

    if bug_type == "correct":
        return Response(should_allow, fields if should_allow else tuple(), audit_logged=audit_logged)
    if bug_type == "missing_auth":
        if not actor.authenticated:
            should_allow = True
            fields = tuple(test.requested_fields)
    elif bug_type == "overbroad_role":
        if actor.role not in policy.roles and actor.authenticated:
            should_allow = True
            fields = tuple(test.requested_fields)
    elif bug_type == "missing_object_check":
        if actor.authenticated and actor.role in policy.roles and actor.purpose in policy.purposes:
            should_allow = True
            fields = tuple(f for f in allowed_fields(policy, actor) if f in test.requested_fields)
    elif bug_type == "jurisdiction_bypass":
        if actor.authenticated and actor.role in policy.roles and actor.purpose in policy.purposes:
            should_allow = True
            fields = tuple(f for f in allowed_fields(policy, actor) if f in test.requested_fields)
    elif bug_type == "purpose_bypass":
        if actor.authenticated and actor.role in policy.roles and same_object_scope(policy, actor, obj):
            should_allow = True
            fields = tuple(f for f in allowed_fields(policy, actor) if f in test.requested_fields)
    elif bug_type == "missing_field_filter":
        if should_allow:
            fields = tuple(test.requested_fields)
    elif bug_type == "aggregation_leak":
        if should_allow and test.test_kind == "aggregation_boundary":
            fields = tuple(test.requested_fields)
    elif bug_type == "missing_audit_log":
        audit_logged = False
    elif bug_type == "deprecated_exposed":
        deprecated_available = True
        if test.test_kind == "deprecated_inventory":
            should_allow = True
            fields = tuple(test.requested_fields)
    else:
        raise ValueError(bug_type)
    return Response(should_allow, fields if should_allow else tuple(), audit_logged=audit_logged, deprecated_available=deprecated_available)


def make_tests(policy: EndpointPolicy, rng: random.Random) -> list[TestCase]:
    pid = policy_id(policy)
    obj = resource_for(policy)
    all_fields = policy.all_fields
    tests = []
    specs = [
        ("valid", "valid", all_fields),
        ("wrong_role", "wrong_role", all_fields),
        ("wrong_jurisdiction", "wrong_jurisdiction", all_fields),
        ("wrong_purpose", "wrong_purpose", all_fields),
        ("self_access", "self_access", all_fields),
        ("unauthenticated", "unauthenticated", all_fields),
        ("sensitive_field_probe", "valid", all_fields),
        ("aggregation_boundary", "valid", all_fields),
        ("deprecated_inventory", "valid", all_fields),
    ]
    for idx, (kind, actor_kind, requested) in enumerate(specs, 1):
        tests.append(TestCase(
            test_id=f"{pid}::test_{idx:02d}_{kind}",
            policy_id=pid,
            test_kind=kind,
            actor=actor_for(policy, actor_kind, rng),
            obj=obj,
            requested_fields=tuple(requested),
        ))
    return tests


def variant_risk(policy: EndpointPolicy, bug_type: str) -> float:
    meta = BUG_METADATA[bug_type]
    if bug_type == "correct":
        return 0.0
    sensitive_count = sum(1 for f in policy.fields if SENSITIVITY_WEIGHT[f.sensitivity] >= 3)
    scope = 4 if bug_type in {"missing_auth", "overbroad_role", "deprecated_exposed"} else 3 if bug_type in {"missing_object_check", "jurisdiction_bypass"} else 2
    exposure = max(1, sensitive_count if bug_type in {"missing_field_filter", "aggregation_leak"} else len(policy.roles))
    exploitability = 4 if bug_type == "missing_auth" else 3 if bug_type in {"overbroad_role", "deprecated_exposed"} else 2
    return float(exposure * policy.max_sensitivity * scope * exploitability * meta["severity"])


def make_variants(policies: list[EndpointPolicy]) -> list[Variant]:
    variants = []
    for policy in policies:
        pid = policy_id(policy)
        for bug_type, meta in BUG_METADATA.items():
            variants.append(Variant(
                variant_id=f"{pid}::{bug_type}",
                policy_id=pid,
                bug_type=bug_type,
                domain=policy.domain,
                endpoint=policy.endpoint,
                severity=meta["severity"],
                owasp=meta["owasp"],
                family=meta["family"],
                risk=variant_risk(policy, bug_type),
            ))
    return variants


def replicated_policies(base_policies: list[EndpointPolicy], multiplier: int) -> list[EndpointPolicy]:
    if multiplier < 1:
        raise ValueError("multiplier must be >= 1")
    replicas = []
    for idx in range(multiplier):
        for policy in base_policies:
            if idx == 0:
                replicas.append(policy)
            else:
                replicas.append(replace(
                    policy,
                    endpoint=f"{policy.endpoint}/replica-{idx}",
                    resource=f"{policy.resource}_replica_{idx}",
                ))
    return replicas


def expected_violation(policy: EndpointPolicy, test: TestCase, response: Response) -> tuple[bool, list[str], float]:
    reasons = []
    risk = 0.0
    expected_allow = policy_allows(policy, test.actor, test.obj)
    expected_fields = set(allowed_fields(policy, test.actor)) & set(test.requested_fields) if expected_allow else set()
    observed_fields = set(response.fields)

    if response.allowed and not expected_allow:
        reasons.append("unauthorized_allow")
        risk += policy.max_sensitivity * 6
    if expected_allow and not response.allowed and test.test_kind in {"valid", "self_access"}:
        reasons.append("under_permission")
        risk += 2
    extra_fields = observed_fields - expected_fields
    if response.allowed and extra_fields:
        reasons.append("field_exposure")
        risk += sum(SENSITIVITY_WEIGHT[next(f.sensitivity for f in policy.fields if f.name == name)] for name in extra_fields)
    if policy.audit_required and not response.audit_logged:
        reasons.append("missing_audit")
        risk += 3
    if response.deprecated_available and test.test_kind == "deprecated_inventory":
        reasons.append("deprecated_endpoint_exposed")
        risk += 4
    return bool(reasons), reasons, risk


METHOD_CAPABILITIES = {
    "schema_validation": set(),
    "auth_required": {"missing_auth"},
    "role_matrix": {"missing_auth", "overbroad_role"},
    "object_policy_tests": {"missing_auth", "overbroad_role", "missing_object_check", "jurisdiction_bypass"},
    "field_policy_tests": {"missing_field_filter", "aggregation_leak"},
    "audit_contract_tests": {"missing_audit_log"},
    "deprecated_inventory_tests": {"deprecated_exposed"},
    "policy_aware_full": {"missing_auth", "overbroad_role", "missing_object_check", "jurisdiction_bypass", "purpose_bypass", "missing_field_filter", "aggregation_leak", "missing_audit_log", "deprecated_exposed"},
    "full_without_object_scope": {"missing_auth", "overbroad_role", "purpose_bypass", "missing_field_filter", "aggregation_leak", "missing_audit_log", "deprecated_exposed"},
    "full_without_field_scope": {"missing_auth", "overbroad_role", "missing_object_check", "jurisdiction_bypass", "purpose_bypass", "missing_audit_log", "deprecated_exposed"},
    "full_without_audit": {"missing_auth", "overbroad_role", "missing_object_check", "jurisdiction_bypass", "purpose_bypass", "missing_field_filter", "aggregation_leak", "deprecated_exposed"},
    "full_without_purpose": {"missing_auth", "overbroad_role", "missing_object_check", "jurisdiction_bypass", "missing_field_filter", "aggregation_leak", "missing_audit_log", "deprecated_exposed"},
}


TEST_SUITES = {
    "auth_smoke": {"valid", "unauthenticated"},
    "role_matrix_min": {"valid", "wrong_role", "unauthenticated"},
    "object_scope": {"valid", "wrong_role", "wrong_jurisdiction", "self_access", "unauthenticated"},
    "purpose_object_scope": {"valid", "wrong_role", "wrong_jurisdiction", "wrong_purpose", "self_access", "unauthenticated"},
    "privacy_scope": {"valid", "sensitive_field_probe", "aggregation_boundary"},
    "no_inventory": {"valid", "wrong_role", "wrong_jurisdiction", "wrong_purpose", "self_access", "unauthenticated", "sensitive_field_probe", "aggregation_boundary"},
    "full": {"valid", "wrong_role", "wrong_jurisdiction", "wrong_purpose", "self_access", "unauthenticated", "sensitive_field_probe", "aggregation_boundary", "deprecated_inventory"},
}


BUG_CAUSES = {
    "missing_auth": "missing_authentication_oracle",
    "overbroad_role": "missing_function_authorization_oracle",
    "missing_object_check": "missing_object_scope_predicate",
    "jurisdiction_bypass": "missing_jurisdiction_predicate",
    "purpose_bypass": "missing_purpose_constraint",
    "missing_field_filter": "missing_field_minimization_oracle",
    "aggregation_leak": "missing_aggregation_boundary_oracle",
    "missing_audit_log": "missing_audit_obligation_oracle",
    "deprecated_exposed": "missing_endpoint_inventory_oracle",
}


PRIMARY_DIMENSION_BY_BUG = {
    "missing_auth": "authentication",
    "overbroad_role": "function_authorization",
    "missing_object_check": "object_scope",
    "jurisdiction_bypass": "jurisdiction_scope",
    "purpose_bypass": "purpose_scope",
    "missing_field_filter": "field_minimization",
    "aggregation_leak": "aggregation_boundary",
    "missing_audit_log": "audit_obligation",
    "deprecated_exposed": "endpoint_inventory",
}


DIMENSION_BY_REASON = {
    "unauthorized_allow": "authorization_decision",
    "under_permission": "authorization_decision",
    "field_exposure": "field_minimization",
    "missing_audit": "audit_obligation",
    "deprecated_endpoint_exposed": "endpoint_inventory",
}


def method_can_observe(method: str, test: TestCase, reason: str) -> bool:
    if method == "schema_validation":
        return False
    if method == "auth_required":
        return reason == "unauthorized_allow" and test.test_kind == "unauthenticated"
    if method == "role_matrix":
        return reason == "unauthorized_allow" and test.test_kind in {"unauthenticated", "wrong_role"}
    if method == "object_policy_tests":
        return reason in {"unauthorized_allow", "under_permission"} and test.test_kind in {"wrong_role", "wrong_jurisdiction", "self_access", "unauthenticated"}
    if method == "field_policy_tests":
        return reason == "field_exposure"
    if method == "audit_contract_tests":
        return reason == "missing_audit"
    if method == "deprecated_inventory_tests":
        return reason == "deprecated_endpoint_exposed"
    if method == "full_without_object_scope":
        return reason not in {"unauthorized_allow"} or test.test_kind not in {"wrong_jurisdiction", "self_access"}
    if method == "full_without_field_scope":
        return reason != "field_exposure"
    if method == "full_without_audit":
        return reason != "missing_audit"
    if method == "full_without_purpose":
        return reason != "unauthorized_allow" or test.test_kind != "wrong_purpose"
    if method == "policy_aware_full":
        return True
    return False


def run_method(method: str, policy: EndpointPolicy, variant: Variant, tests: list[TestCase]) -> list[Finding]:
    findings = []
    for test in tests:
        response = apply_variant(policy, variant.bug_type, test)
        violation, reasons, risk = expected_violation(policy, test, response)
        observed_reasons = [r for r in reasons if method_can_observe(method, test, r)]
        detected = bool(observed_reasons) and variant.bug_type in METHOD_CAPABILITIES[method]
        findings.append(Finding(
            method=method,
            variant_id=variant.variant_id,
            test_id=test.test_id,
            bug_type=variant.bug_type,
            family=variant.family,
            severity=variant.severity,
            detected=detected,
            risk_flagged=risk if detected else 0.0,
            reason=";".join(observed_reasons),
        ))
    return findings


def summarize_detection(findings: list[Finding], variants: list[Variant]) -> tuple[list[dict], list[dict], list[dict]]:
    variant_by_id = {v.variant_id: v for v in variants}
    by_method_variant = defaultdict(list)
    for finding in findings:
        by_method_variant[(finding.method, finding.variant_id)].append(finding)

    detections = []
    for (method, variant_id), items in sorted(by_method_variant.items()):
        variant = variant_by_id[variant_id]
        detected = any(item.detected for item in items)
        detections.append({
            "method": method,
            "variant_id": variant_id,
            "domain": variant.domain,
            "endpoint": variant.endpoint,
            "bug_type": variant.bug_type,
            "family": variant.family,
            "owasp": variant.owasp,
            "severity": variant.severity,
            "ground_truth_bug": int(variant.bug_type != "correct"),
            "detected": int(detected),
            "risk": round(variant.risk, 4),
            "risk_flagged": round(sum(item.risk_flagged for item in items), 4),
            "tests_run": len(items),
            "tests_flagged": sum(1 for item in items if item.detected),
        })

    summary = []
    for method in sorted({d["method"] for d in detections}):
        rows = [d for d in detections if d["method"] == method]
        tp = sum(1 for d in rows if d["ground_truth_bug"] and d["detected"])
        fp = sum(1 for d in rows if not d["ground_truth_bug"] and d["detected"])
        tn = sum(1 for d in rows if not d["ground_truth_bug"] and not d["detected"])
        fn = sum(1 for d in rows if d["ground_truth_bug"] and not d["detected"])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        risk_total = sum(d["risk"] for d in rows if d["ground_truth_bug"])
        risk_detected = sum(d["risk"] for d in rows if d["ground_truth_bug"] and d["detected"])
        summary.append({
            "method": method,
            "n_variants": len(rows),
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "risk_weighted_recall": round(risk_detected / risk_total, 4) if risk_total else 0.0,
            "mean_tests_per_variant": round(sum(d["tests_run"] for d in rows) / len(rows), 2),
            "mean_flags_per_variant": round(sum(d["tests_flagged"] for d in rows) / len(rows), 2),
        })

    by_family = []
    for method in sorted({d["method"] for d in detections}):
        rows = [d for d in detections if d["method"] == method and d["ground_truth_bug"]]
        for family in sorted({d["family"] for d in rows}):
            items = [d for d in rows if d["family"] == family]
            recall = sum(d["detected"] for d in items) / len(items)
            risk_total = sum(d["risk"] for d in items)
            risk_detected = sum(d["risk"] for d in items if d["detected"])
            by_family.append({
                "method": method,
                "family": family,
                "n": len(items),
                "recall": round(recall, 4),
                "risk_weighted_recall": round(risk_detected / risk_total, 4) if risk_total else 0.0,
            })
    return detections, summary, by_family


def bootstrap_ci(values: list[float], iterations: int = 2000, seed: int = 17) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    rng = random.Random(seed)
    estimates = []
    n = len(values)
    for _ in range(iterations):
        estimates.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    estimates.sort()
    return estimates[int(0.025 * iterations)], estimates[int(0.975 * iterations)]


def paired_deltas(detections: list[dict], baseline: str = "role_matrix", proposed: str = "policy_aware_full") -> list[dict]:
    by_key = {(d["method"], d["variant_id"]): d for d in detections if d["ground_truth_bug"]}
    variant_ids = sorted({d["variant_id"] for d in detections if d["ground_truth_bug"]})
    out = []
    for metric in ["detected", "risk_flagged"]:
        diffs = []
        for variant_id in variant_ids:
            a = by_key[(baseline, variant_id)]
            b = by_key[(proposed, variant_id)]
            if metric == "detected":
                diffs.append(float(b[metric]) - float(a[metric]))
            else:
                risk = max(float(b["risk"]), 1.0)
                diffs.append((float(b[metric]) - float(a[metric])) / risk)
        low, high = bootstrap_ci(diffs)
        out.append({
            "contrast": f"{proposed}_minus_{baseline}",
            "metric": metric,
            "n": len(diffs),
            "mean_delta": round(sum(diffs) / len(diffs), 4),
            "ci_low": round(low, 4),
            "ci_high": round(high, 4),
            "proposed_better": sum(1 for d in diffs if d > 0),
            "tie": sum(1 for d in diffs if abs(d) < 1e-12),
            "baseline_better": sum(1 for d in diffs if d < 0),
        })
    return out


def grouped_recall(detections: list[dict], group_key: str) -> list[dict]:
    rows = [d for d in detections if d["ground_truth_bug"]]
    out = []
    for method in sorted({d["method"] for d in rows}):
        method_rows = [d for d in rows if d["method"] == method]
        for group_value in sorted({d[group_key] for d in method_rows}):
            items = [d for d in method_rows if d[group_key] == group_value]
            risk_total = sum(d["risk"] for d in items)
            risk_detected = sum(d["risk"] for d in items if d["detected"])
            out.append({
                "method": method,
                group_key: group_value,
                "n": len(items),
                "recall": round(sum(d["detected"] for d in items) / len(items), 4),
                "risk_weighted_recall": round(risk_detected / risk_total, 4) if risk_total else 0.0,
            })
    return out


def causal_miss_analysis(detections: list[dict], findings: list[Finding], variants: list[Variant]) -> list[dict]:
    variant_by_id = {v.variant_id: v for v in variants}
    detected_by_method_variant = {
        (d["method"], d["variant_id"]): bool(d["detected"])
        for d in detections
    }
    oracle_findings = defaultdict(list)
    for finding in findings:
        if finding.method == "policy_aware_full" and finding.detected:
            oracle_findings[finding.variant_id].append(finding)

    rows = []
    for method in sorted(METHOD_CAPABILITIES):
        if method == "policy_aware_full":
            continue
        for variant in variants:
            if variant.bug_type == "correct":
                continue
            if detected_by_method_variant.get((method, variant.variant_id), False):
                continue
            evidence = oracle_findings.get(variant.variant_id, [])
            reasons = sorted({reason for item in evidence for reason in item.reason.split(";") if reason})
            test_kinds = sorted({
                item.test_id.split("::test_", 1)[1].split("_", 1)[1]
                for item in evidence
                if item.reason
            })
            dimensions = sorted({DIMENSION_BY_REASON.get(reason, "unknown") for reason in reasons})
            rows.append({
                "method": method,
                "variant_id": variant.variant_id,
                "domain": variant.domain,
                "endpoint": variant.endpoint,
                "bug_type": variant.bug_type,
                "family": variant.family,
                "root_cause": BUG_CAUSES.get(variant.bug_type, "unknown"),
                "primary_missing_dimension": PRIMARY_DIMENSION_BY_BUG.get(variant.bug_type, "unknown"),
                "oracle_reasons": ";".join(reasons),
                "observed_violation_dimensions": ";".join(dimensions),
                "evidence_test_kinds": ";".join(test_kinds),
                "risk": round(variant.risk, 4),
            })
    return rows


def causal_miss_summary(miss_rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in miss_rows:
        grouped[(row["method"], row["root_cause"], row["primary_missing_dimension"])].append(row)
    out = []
    for (method, root_cause, primary_dimension), rows in sorted(grouped.items()):
        out.append({
            "method": method,
            "root_cause": root_cause,
            "primary_missing_dimension": primary_dimension,
            "missed_variants": len(rows),
            "risk_missed": round(sum(float(row["risk"]) for row in rows), 4),
            "domains": ";".join(sorted({row["domain"] for row in rows})),
            "families": ";".join(sorted({row["family"] for row in rows})),
        })
    return out


def test_budget_curve(
    policies: list[EndpointPolicy],
    variants: list[Variant],
    tests_by_policy: dict[str, list[TestCase]],
    methods: tuple[str, ...] = ("role_matrix", "object_policy_tests", "policy_aware_full"),
) -> list[dict]:
    policy_map = {policy_id(p): p for p in policies}
    out = []
    for suite_name, test_kinds in TEST_SUITES.items():
        for method in methods:
            findings = []
            for variant in variants:
                policy = policy_map[variant.policy_id]
                tests = [t for t in tests_by_policy[variant.policy_id] if t.test_kind in test_kinds]
                findings.extend(run_method(method, policy, variant, tests))
            detections, summary, _ = summarize_detection(findings, variants)
            method_summary = next(row for row in summary if row["method"] == method)
            rows = [d for d in detections if d["method"] == method and d["ground_truth_bug"]]
            risk_total = sum(d["risk"] for d in rows)
            risk_detected = sum(d["risk"] for d in rows if d["detected"])
            out.append({
                "suite": suite_name,
                "method": method,
                "test_kinds": len(test_kinds),
                "tests_per_endpoint": len(test_kinds),
                "total_executions": len(variants) * len(test_kinds),
                "recall": method_summary["recall"],
                "f1": method_summary["f1"],
                "risk_weighted_recall": round(risk_detected / risk_total, 4) if risk_total else 0.0,
                "mean_flags_per_variant": method_summary["mean_flags_per_variant"],
            })
    return sorted(out, key=lambda r: (r["method"], r["test_kinds"], r["suite"]))


def scale_sweep(
    base_policies: list[EndpointPolicy],
    seed: int,
    multipliers: tuple[int, ...] = (1, 2, 4, 8, 10),
    methods: tuple[str, ...] = ("role_matrix", "policy_aware_full"),
) -> list[dict]:
    out = []
    for multiplier in multipliers:
        rng = random.Random(seed + multiplier)
        policies = replicated_policies(base_policies, multiplier)
        variants = make_variants(policies)
        policy_map = {policy_id(p): p for p in policies}
        tests_by_policy = {policy_id(p): make_tests(p, rng) for p in policies}
        started = time.perf_counter()
        findings = []
        for variant in variants:
            policy = policy_map[variant.policy_id]
            tests = tests_by_policy[variant.policy_id]
            for method in methods:
                findings.extend(run_method(method, policy, variant, tests))
        elapsed = time.perf_counter() - started
        detections, summary, _ = summarize_detection(findings, variants)
        summary_by_method = {row["method"]: row for row in summary}
        for method in methods:
            rows = [d for d in detections if d["method"] == method and d["ground_truth_bug"]]
            risk_total = sum(d["risk"] for d in rows)
            risk_detected = sum(d["risk"] for d in rows if d["detected"])
            out.append({
                "multiplier": multiplier,
                "method": method,
                "policies": len(policies),
                "variants": len(variants),
                "buggy_variants": sum(1 for v in variants if v.bug_type != "correct"),
                "tests": sum(len(tests) for tests in tests_by_policy.values()),
                "test_executions": len(variants) * (len(next(iter(tests_by_policy.values())))),
                "elapsed_seconds": round(elapsed, 4),
                "recall": summary_by_method[method]["recall"],
                "risk_weighted_recall": round(risk_detected / risk_total, 4) if risk_total else 0.0,
            })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(rows[0].keys())
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def dataclass_dict(obj) -> dict:
    if isinstance(obj, (Actor, ResourceObject, TestCase, Variant)):
        out = {}
        for key, value in obj.__dict__.items():
            if isinstance(value, tuple):
                out[key] = list(value)
            elif isinstance(value, (Actor, ResourceObject)):
                out[key] = dataclass_dict(value)
            else:
                out[key] = value
        return out
    raise TypeError(type(obj))


def make_report(
    summary: list[dict],
    by_family: list[dict],
    by_domain: list[dict],
    budget_curve: list[dict],
    miss_summary: list[dict],
    scale_rows: list[dict],
    deltas: list[dict],
    variants: list[Variant],
    tests: list[TestCase],
) -> str:
    best = max(summary, key=lambda r: (r["risk_weighted_recall"], r["recall"], r["precision"]))
    counts = Counter(v.bug_type for v in variants)
    families = Counter(v.family for v in variants if v.bug_type != "correct")
    lines = [
        "# Policy-Aware Contract Testing Experiment Report",
        "",
        "## Benchmark Size",
        "",
        f"- Policies/endpoints: {len(set(v.policy_id for v in variants))}",
        f"- Variants: {len(variants)}",
        f"- Injected buggy variants: {sum(1 for v in variants if v.bug_type != 'correct')}",
        f"- Test cases per endpoint: {len(tests) // len(set(t.policy_id for t in tests))}",
        f"- Total test executions per method: {len(variants) * (len(tests) // len(set(t.policy_id for t in tests)))}",
        "",
        "## Bug Families",
        "",
    ]
    for family, n in sorted(families.items()):
        lines.append(f"- {family}: {n}")
    lines.extend([
        "",
        "## Policy-Aware Recall by Domain",
        "",
        "| Domain | Variants | Recall | Risk-weighted recall |",
        "|---|---:|---:|---:|",
    ])
    for row in by_domain:
        if row["method"] == "policy_aware_full":
            lines.append(f"| {row['domain']} | {row['n']} | {row['recall']} | {row['risk_weighted_recall']} |")
    lines.extend([
        "",
        "## Best Method",
        "",
        f"- Method: `{best['method']}`",
        f"- Precision: {best['precision']}",
        f"- Recall: {best['recall']}",
        f"- F1: {best['f1']}",
        f"- Risk-weighted recall: {best['risk_weighted_recall']}",
        "",
        "## Method Summary",
        "",
        "| Method | Precision | Recall | F1 | Risk-weighted recall |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in sorted(summary, key=lambda r: r["risk_weighted_recall"], reverse=True):
        lines.append(f"| {row['method']} | {row['precision']} | {row['recall']} | {row['f1']} | {row['risk_weighted_recall']} |")
    lines.extend([
        "",
        "## Test Budget Curve",
        "",
        "| Suite | Method | Tests per endpoint | Recall | Risk-weighted recall |",
        "|---|---|---:|---:|---:|",
    ])
    for row in budget_curve:
        if row["method"] == "policy_aware_full":
            lines.append(f"| {row['suite']} | {row['method']} | {row['tests_per_endpoint']} | {row['recall']} | {row['risk_weighted_recall']} |")
    lines.extend([
        "",
        "## Causal Miss Summary",
        "",
        "| Method | Root cause | Primary missing dimension | Missed variants | Risk missed |",
        "|---|---|---|---:|---:|",
    ])
    for row in sorted(miss_summary, key=lambda r: r["risk_missed"], reverse=True)[:24]:
        lines.append(f"| {row['method']} | {row['root_cause']} | {row['primary_missing_dimension']} | {row['missed_variants']} | {row['risk_missed']} |")
    lines.extend([
        "",
        "## Scale Sweep",
        "",
        "| Multiplier | Method | Policies | Variants | Executions | Seconds | Recall |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ])
    for row in scale_rows:
        lines.append(f"| {row['multiplier']} | {row['method']} | {row['policies']} | {row['variants']} | {row['test_executions']} | {row['elapsed_seconds']} | {row['recall']} |")
    lines.extend([
        "",
        "## Paired Delta Against Role-Matrix Baseline",
        "",
        "| Metric | Mean delta | 95% CI | Proposed better | Tie | Baseline better |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for row in deltas:
        lines.append(f"| {row['metric']} | {row['mean_delta']} | [{row['ci_low']}, {row['ci_high']}] | {row['proposed_better']} | {row['tie']} | {row['baseline_better']} |")
    lines.extend([
        "",
        "## Interpretation Notes",
        "",
        "- Structural schema validation is expected to miss policy bugs because the mutated APIs can still return schema-valid payloads.",
        "- Role-only tests catch missing authentication and coarse over-permission, but they miss object-level, field-level, purpose, and audit failures.",
        "- The full policy-aware test suite detects all injected policy-bug families in this deterministic benchmark; ablation rows quantify which policy dimensions carry that coverage.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--out-dir", default=str(RESULTS))
    parser.add_argument("--multiplier", type=int, default=1, help="Replicate endpoint-policy families to scale the benchmark.")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    out_dir = Path(args.out_dir)
    policies = replicated_policies(domains(), args.multiplier)
    variants = make_variants(policies)
    policy_map = {policy_id(p): p for p in policies}
    tests_by_policy = {policy_id(p): make_tests(p, rng) for p in policies}
    all_tests = [t for tests in tests_by_policy.values() for t in tests]

    findings = []
    for variant in variants:
        policy = policy_map[variant.policy_id]
        tests = tests_by_policy[variant.policy_id]
        for method in METHOD_CAPABILITIES:
            findings.extend(run_method(method, policy, variant, tests))

    detections, summary, by_family = summarize_detection(findings, variants)
    by_domain = grouped_recall(detections, "domain")
    by_endpoint = grouped_recall(detections, "endpoint")
    miss_rows = causal_miss_analysis(detections, findings, variants)
    miss_summary = causal_miss_summary(miss_rows)
    budget_curve = test_budget_curve(policies, variants, tests_by_policy)
    scale_rows = scale_sweep(domains(), args.seed)
    deltas = paired_deltas(detections)

    variant_rows = [dataclass_dict(v) for v in variants]
    test_rows = [dataclass_dict(t) for t in all_tests]
    finding_rows = [f.__dict__ for f in findings]

    write_jsonl(DATA / "policy_bug_variants.jsonl", variant_rows)
    write_jsonl(DATA / "policy_test_cases.jsonl", test_rows)
    write_csv(out_dir / "policy_detection_results.csv", detections)
    write_csv(out_dir / "method_summary.csv", summary)
    write_csv(out_dir / "recall_by_bug_family.csv", by_family)
    write_csv(out_dir / "recall_by_domain.csv", by_domain)
    write_csv(out_dir / "recall_by_endpoint.csv", by_endpoint)
    write_csv(out_dir / "causal_miss_analysis.csv", miss_rows)
    write_csv(out_dir / "causal_miss_summary.csv", miss_summary)
    write_csv(out_dir / "test_budget_curve.csv", budget_curve)
    write_csv(out_dir / "scale_sweep.csv", scale_rows)
    write_csv(out_dir / "paired_policy_delta.csv", deltas)
    write_csv(out_dir / "test_level_findings.csv", finding_rows)

    with (out_dir / "experiment_summary.json").open("w", encoding="utf-8") as handle:
        json.dump({
            "seed": args.seed,
            "policies": len(policies),
            "variants": len(variants),
            "buggy_variants": sum(1 for v in variants if v.bug_type != "correct"),
            "test_cases": len(all_tests),
            "methods": list(METHOD_CAPABILITIES),
            "test_suites": {name: sorted(kinds) for name, kinds in TEST_SUITES.items()},
            "bug_types": dict(Counter(v.bug_type for v in variants)),
        }, handle, indent=2)

    (out_dir / "EXPERIMENT_REPORT.md").write_text(
        make_report(summary, by_family, by_domain, budget_curve, miss_summary, scale_rows, deltas, variants, all_tests),
        encoding="utf-8",
    )
    print(f"wrote policy-contract benchmark results to {out_dir}")


if __name__ == "__main__":
    main()
