"uploaded": false,
       "reason": "no_impl_folder"
     }

● Plan "Split PlanDataProvider: Separate Domain Service from TUI Data Assembly" saved as draft PR #8804.
  URL: https://github.com/dagster-io/erk/pull/8804

● Plan #8804 saved. Here are your next steps:

  Implement plan #8804:
  In current wt:    source "$(erk br co --for-plan 8804 --script)" && erk implement
    (dangerously):  source "$(erk br co --for-plan 8804 --script)" && erk implement -d
  In new wt:        source "$(erk br co --new-slot --for-plan 8804 --script)" && erk implement
    (dangerously):  source "$(erk br co --new-slot --for-plan 8804 --script)" && erk implement -d

  Checkout plan #8804:
  In current wt:  erk br co --for-plan 8804
  In new wt:      erk br co --new-slot --for-plan 8804

  Dispatch plan #8804:
  CLI command:    erk pr dispatch 8804
  Slash command:  /erk:pr-dispatch  Implement plan #8804:



  In current wt:    source "$(erk br co --for-plan 8804 --script)" && erk implement
    (dangerously):  source "$(erk br co --for-plan 8804 --script)" && erk implement -d

✻ Crunched for 4m 19s

❯ /erk:pr-dispatch


-------

In this screen I do not believe we need the sources in 

  Implement plan #8804:
  In current wt:    source "$(erk br co --for-plan 8804 --script)" && erk implement
    (dangerously):  source "$(erk br co --for-plan 8804 --script)" && erk implement -d


please eliminate them and just call erk directly
