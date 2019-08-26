from smart import Rule as _ 

rules = (

  _("morning lamp").
    If("week_day", 0, 1, 2, 3, 4).
    If("later_than", 20, 00).
    Not("later_than", 23, 00).
    Once("device_online", "Macbook", "iPhone", op="or").
    Then("plug", "on", "lamp").
    Then("plug", "off", "computer")

)
