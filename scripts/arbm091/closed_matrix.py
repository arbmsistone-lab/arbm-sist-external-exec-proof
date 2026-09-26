"""Canonical closed matrix for ARBM Task 091.

Single source of truth for the 75 semantic transaction lanes plus Section E.
Rows with equivalent old/new values are preservation assertions, not WPS edits.
"""
from __future__ import annotations
from collections import Counter

MATRIX_SCHEMA = 1
EXPECTED_TRANSACTION_COUNT = 75
EXPECTED_SECTION_E_COUNT = 1
EXPECTED_BY_SLIDE = {1:5,2:5,3:6,4:13,6:9,7:2,8:3,9:5,11:3,12:6,13:18}
EXPECTED_PRESERVATION_IDS = ("T025","T068")

TASK091_SPATIAL_TEXT_EDITS = (
    # slide, x, y, visible draft text, final text
    (1, 745, 335, 'Growth Plan Draft', 'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'),
    (1, 738, 503, 'Planning posture: accelerate growth through H2 scale-up',
                    'Northstar Cloud\nPrepared for July Operating Committee review\nPlanning posture: stabilize and recover with disciplined sequencing'),
    (1, 1338, 393, '$42.8M', '$40.9M'),
    (1, 1338, 511, '$2.6M', '$2.8M'),
    (1, 1338, 630, '214', '206'),
    (2, 558, 364, '$42.8M', '$40.9M'),
    (2, 792, 364, '112%', '104%'),
    (2, 1026, 364, '$2.6M', '$2.8M'),
    (2, 1245, 364, '19 mo', '17 mo'),
    (2, 1439, 364, '214', '206'),
    # KPI scorecard structured H2 column.
    (3, 843, 404, '$42.8M', '$40.9M'),
    (3, 843, 465, '112%', '104%'),
    (3, 843, 525, '74%', '71%'),
    (3, 843, 586, '$2.6M', '$2.8M'),
    (3, 843, 646, '2', '3'),
    (3, 843, 707, '214', '206'),
    # ARR bridge individual value/label shapes.
    (4, 617, 360, '+1.2', '+0.7'),
    (4, 615, 752, 'New logo mix', 'Renewal saves'),
    (4, 728, 360, '+0.6', '+0.4'),
    (4, 727, 752, 'Price uplift', 'Pricing discipline'),
    (4, 839, 360, '+0.8', '-0.6'),
    (4, 838, 752, 'Usage expansion', 'Migration delay'),
    (4, 950, 360, '+0.4', '-0.5'),
    (4, 949, 752, 'International pilot', 'Support credits'),
    (4, 1062, 360, '-0.3', '-0.3'),
    (4, 1060, 752, 'Hiring drag', 'International Pilot stop'),
    (4, 1173, 360, '+0.5', '+1.6'),
    (4, 1171, 752, 'Partner channel', 'Partner stabilization'),
    (4, 1284, 360, '42.8', '40.9'),
    # Headcount table: expose separate Reliability and Growth Ops freeze rows.
    (6, 1198, 400, 'Platform & Reliability', 'Platform'),
    (6, 1322, 400, 'Scale up', 'Selective backfill'),
    (6, 1447, 400, '8', '2'),
    (6, 1198, 450, 'Growth Ops', 'Reliability'),
    (6, 1322, 450, 'Expand', 'Protected hiring'),
    (6, 1447, 450, '5', '3'),
    (6, 1198, 500, 'GTM', 'Growth Ops'),
    (6, 1322, 500, 'Selective add', 'Freeze'),
    (6, 1447, 500, '6', '0'),
    # Risk titles: remove closed launch risk and introduce two final H2 risks.
    (7, 717, 383, 'Regional launch readiness', 'Vendor SLA breach'),
    (7, 571, 499, 'Data privacy review', 'Data migration cutover failure'),
    # Dependency map final workstreams.
    (8, 576, 408, 'Platform uplift', 'Reliability Hardening'),
    (8, 850, 408, 'Expansion Sprint', 'Customer Retention Plays'),
    (8, 1123, 408, 'International Pilot', 'Data Migration'),
    # Roadmap visible lanes/text.
    (9, 800, 195, 'H2 Growth Roadmap', 'H2 Stabilize-and-Recover Roadmap'),
    (9, 505, 455, 'Expansion Sprint', 'Reliability Hardening'),
    (9, 901, 453, 'Expansion Sprint', 'Reliability Hardening'),
    (9, 505, 535, 'International Pilot', 'Data Migration'),
    (9, 1013, 533, 'International Pilot', 'Data Migration'),
    # Decision requests.
    (11, 234, 391, 'Confirm Expansion Sprint funding', 'Protect Reliability Hardening capacity'),
    (11, 609, 391, 'Approve International Pilot launch window', 'Sequence Data Migration cutover'),
    (11, 984, 391, 'Maintain current GTM hiring mix', 'Freeze non-critical hiring'),
    # Appendix KPI H2 column.
    (12, 1396, 466, '42.8', '40.9'),
    (12, 1396, 526, '112', '104'),
    (12, 1396, 586, '74', '71'),
    (12, 1396, 646, '2.6', '2.8'),
    (12, 1396, 705, '214', '206'),
    (12, 1396, 765, '2', '3'),
    # Appendix milestone tracker.
    (13, 544, 536, 'Expansion Sprint launch', 'Incident runbook rollout'),
    (13, 804, 536, 'Growth Ops', 'Reliability Hardening'),
    (13, 1064, 536, 'Sep 01', 'Aug 22'),
    (13, 1323, 536, 'Green', 'Amber'),
    (13, 544, 581, 'International Pilot kickoff', 'Cutover rehearsal complete'),
    (13, 804, 581, 'GTM', 'Data Migration'),
    (13, 1064, 581, 'Sep 15', 'Sep 19'),
    (13, 1323, 581, 'Green', 'Amber'),
    (13, 544, 627, 'Self-serve pricing release', 'Renewal intervention playbook'),
    (13, 1064, 627, 'Oct 03', 'Oct 10'),
    (13, 544, 672, 'Renewals dashboard v2', 'Renewals dashboard v2'),
    (13, 1064, 672, 'Oct 21', 'Oct 24'),
    (13, 544, 718, 'Regional playbook rollout', 'Wave 1 migration complete'),
    (13, 804, 718, 'Ops', 'Data Migration'),
    (13, 1064, 718, 'Nov 11', 'Nov 14'),
    (13, 544, 763, 'Global launch readiness review', 'Recovery review with OpCom'),
    (13, 1064, 763, 'Dec 04', 'Dec 05'),
    (13, 1323, 763, 'Red', 'Green'),
)

TASK091_SECTION_E_FORMAT = {
    'slide': 3,
    'shape_id': 16,
    'shape_name': 'KpiReadout_Body',
    'text_fingerprint': '• Burn improvement relies on expansion payback from Q4.',
    'font_decrements': 7,
}


def _norm(value):
    return " ".join(str(value or "").replace("\u200b","").casefold().split())


def matrix_rows():
    rows=[]
    for index,(slide,x,y,old,new) in enumerate(TASK091_SPATIAL_TEXT_EDITS,1):
        mode="preserve" if _norm(old)==_norm(new) else "mutate"
        rows.append({
            "id":f"T{index:03d}",
            "slide":int(slide),
            "hint_x":int(x),
            "hint_y":int(y),
            "old":str(old),
            "new":str(new),
            "mode":mode,
        })
    return tuple(rows)


def matrix_summary():
    rows=matrix_rows()
    modes=Counter(row["mode"] for row in rows)
    by_slide=Counter(row["slide"] for row in rows)
    return {
        "schema":MATRIX_SCHEMA,
        "transactions":len(rows),
        "mutations":int(modes.get("mutate",0)),
        "preservations":int(modes.get("preserve",0)),
        "section_e":EXPECTED_SECTION_E_COUNT,
        "by_slide":dict(sorted(by_slide.items())),
        "preservation_ids":[row["id"] for row in rows if row["mode"]=="preserve"],
    }


def assert_closed_matrix():
    rows=matrix_rows()
    summary=matrix_summary()
    assert summary["transactions"]==EXPECTED_TRANSACTION_COUNT, summary
    assert summary["mutations"]==73, summary
    assert summary["preservations"]==2, summary
    assert summary["section_e"]==1, summary
    assert summary["by_slide"]==EXPECTED_BY_SLIDE, summary
    assert tuple(summary["preservation_ids"])==EXPECTED_PRESERVATION_IDS, summary
    assert len({row["id"] for row in rows})==EXPECTED_TRANSACTION_COUNT
    assert len({(row["slide"],row["hint_x"],row["hint_y"]) for row in rows})==EXPECTED_TRANSACTION_COUNT
    for row in rows:
        assert row["old"] and row["new"], row
        if row["mode"]=="mutate":
            assert _norm(row["old"])!=_norm(row["new"]), row
        else:
            assert _norm(row["old"])==_norm(row["new"]), row
    spec=TASK091_SECTION_E_FORMAT
    assert spec=={
        "slide":3,
        "shape_id":16,
        "shape_name":"KpiReadout_Body",
        "text_fingerprint":"• Burn improvement relies on expansion payback from Q4.",
        "font_decrements":7,
    }, spec
    return summary
