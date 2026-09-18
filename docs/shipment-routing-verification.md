# Shipment routing verification — 3.0.0

Verified locally on 18 September 2026 with synthetic records.

## Automated checks

- Production frontend build passed; the existing bundle-size warning remains.
- Complete frontend run: 598 tests passed. A subsequently added intermediate
  operator receipt regression passed together with all eight delivery page tests.
- Full backend run: 3,159 passed and 21 skipped, with one obsolete rate-limit
  expectation for the retired temporary endpoint. That expectation was corrected
  and passed in a subsequent focused run.
- After the final shipment summary and document changes, 121 focused backend tests
  passed. After the intermediate operator permission adjustment, all 64 routing
  and delivery tests passed, including its new regression.
- Version consistency, third-party inventory (218 components), and diff whitespace
  checks passed. No dependency was added.

## Browser checks

- Created and finalized a document-free shipment of ten steel plates, distributed
  six to receiver A and four to receiver B, with one pickup location.
- The delivery copied all three addresses and generated the two consecutive legs;
  only receiver B's allocation continued on the second leg.
- Planned and released the first leg. A missing document date blocked issuance;
  its error now names the missing field.
- Saved independent document inputs for receiver A and verified that receiver B
  did not inherit them. Combining both recipients disabled document issuance.
- Issued receiver A's packing list successfully as a stored PDF.
- Checked shipment addresses, distribution, shipment detail and delivery screens
  at a 390 × 844 viewport without page-wide horizontal overflow. Restored the
  desktop viewport afterward.
- Confirmed that the shipment list shows document-free prepared cargo as ready.

The browser check covers this ordinary-goods workflow. DG split confirmations,
review invalidation, migration preservation, reservations and recipient isolation
were covered by automated tests. No production data was changed or release
published during this implementation.

## GitHub release check

The first PR run (35344639481) passed frontend and rights checks. The backend
job hit its 15-minute wall-clock limit after reaching 90% with no reported test
failures. It was cancelled before a final result, so image builds, merge and
release did not run. The backend job now allows 30 minutes including setup and
reports its 20 slowest tests; all original test and publication gates remain.
