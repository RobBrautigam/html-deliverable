# Northwind Retail: the first quarter on the new platform

Three months after the cutover, the numbers are in. This is what changed, what it cost, and the
one decision still open. Every figure below is read from the finance export of April 1, 2026.

## 1. Where the quarter landed

Revenue through the new checkout came to $1,240,000 against a $1,000,000 plan, and the cost per
order fell from $4.20 to $2.80. The gain is not the platform on its own: two thirds of it is the
new returns flow, which stopped 1,100 orders a month from being refunded on the first contact.

The one number that did not move is the average basket, which held at $64.00 all quarter. That was
the plan. A basket that jumps in the first quarter of a replatform usually means the discount rules
came across wrong.

## 2. The picture

The path an order takes, end to end, and where the two remaining manual steps sit.

<figure class="flow" aria-label="How an order moves through the new platform">
  <script type="application/json" class="flow-data">
  {
    "title": "How an order moves through the new platform",
    "caption": "Two steps are still done by hand. Both are in the returns lane, and both are on the roadmap for the second quarter.",
    "lanes": [
      {"id": "shopper", "label": "SHOPPER", "tone": "acc-2"},
      {"id": "platform", "label": "PLATFORM", "tone": "acc"},
      {"id": "team", "label": "OUR TEAM", "tone": "violet"}
    ],
    "nodes": [
      {"id": "cart", "col": 0, "lane": "shopper", "label": "Basket and checkout", "note": "LIVE", "tone": "green"},
      {"id": "pay", "col": 1, "lane": "platform", "label": "Payment authorized", "note": "LIVE", "tone": "green"},
      {"id": "pick", "col": 2, "lane": "platform", "label": "Warehouse pick", "note": "LIVE", "tone": "green"},
      {"id": "ship", "col": 3, "lane": "platform", "label": "Carrier handoff", "note": "LIVE", "tone": "green"},
      {"id": "ret", "col": 4, "lane": "shopper", "label": "Return requested", "note": "SELF SERVE", "tone": "acc-2"},
      {"id": "grade", "col": 5, "lane": "team", "label": "Condition graded", "note": "BY HAND", "tone": "amber"},
      {"id": "credit", "col": 6, "lane": "team", "label": "Credit issued", "note": "BY HAND", "tone": "amber"}
    ],
    "edges": [
      {"from": "cart", "to": "pay"},
      {"from": "pay", "to": "pick"},
      {"from": "pick", "to": "ship"},
      {"from": "ship", "to": "ret"},
      {"from": "ret", "to": "grade"},
      {"from": "grade", "to": "credit"}
    ],
    "marks": [
      {"node": "grade", "label": "Q1"},
      {"node": "credit", "label": "Q2"}
    ]
  }
  </script>
</figure>

## 3. The numbers, month by month

Every row is read from the finance export. Sort any column, or filter the rows with the box above
the table.

| Month | Orders | Revenue | Cost per order | Returns |
|---|---|---|---|---|
| January | 12,000 | $380,000 | $3.40 | 1,400 |
| February | 13,500 | $410,000 | $3.00 | 1,250 |
| March | 15,000 | $450,000 | $2.80 | 1,100 |
| April (part) | 5,200 | $156,000 | $2.75 | 380 |
| May (forecast) | 16,000 | $480,000 | $2.70 | 1,000 |
| June (forecast) | 17,000 | $510,000 | $2.65 | 950 |

The April row is three weeks of actuals, not a month. The two forecast rows are the plan, and they
are the only figures on this page that are not measured.

## 4. What it cost

The build came in at $180,000 against a $200,000 budget, and the platform's own license is $4,000
a month. Against a cost-per-order saving of $1.40 on roughly 15,000 orders a month, the build pays
for itself in the eighth month after cutover.

## 5. The decision still open

The returns lane has two manual steps, and only one of them is worth automating this quarter.

- **Condition grading** takes about 90 seconds per return and needs a human eye on the item. The
  cost of getting it wrong is a credit issued on an item that cannot be resold.
- **Credit issuing** takes about 40 seconds and is entirely mechanical once the grade is set.

The recommendation is to automate credit issuing in the second quarter and leave grading with the
team, which saves about 12 hours a month at no risk. The full write-up is at
https://docs.example.com/northwind/returns-plan and the cost model is at
https://docs.example.com/northwind/cost-model .

## 6. What happens next

A short list, in order:

1. Sign off the returns plan, or say which part of it to change.
2. Book the second-quarter kickoff for the week of April 20.
3. Hand the cost model to finance so the eighth-month payback lands in the forecast.
