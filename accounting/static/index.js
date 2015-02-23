"use strict";
    
$(function() {
    $( "#submit_button" ).click(validate);
})

function validate() {
    var policy_number = parseInt( $( "#policy_number" ).val() );
    var supplied_date = $( "#date_box" ).val();
    
    if (!Number.isInteger(policy_number)) {
        $( "#policy_number" ).val("");
        $( "#submit_error" ).text("The policy number you entered was not recognized, please try again.");
        return;
    }
    
    // if the user leaves date blank just pass the empty string, no need to verify format.
    if (supplied_date != "") {
        //naive format match, doesn't check whether the date is actually valid.
        var reg = /^\d{4}[\/\-](0?[1-9]|1[012])[\/\-](0?[1-9]|[12][0-9]|3[01])$/;
        if (!reg.test(supplied_date)) {
            $( "#date_box" ).val("");
            $( "#submit_error" ).text("The date you entered was not recognized, please try again.");
            return;
        }
    }
    
    //clear the error box in case they hit the back button
    $( "#submit_error" ).text("");
    $( "#policy_form" ).submit();
}

if (!Number.isInteger) {
  Number.isInteger = function isInteger(nVal) {
    return typeof nVal === 'number'
      && isFinite(nVal)
      && nVal > -9007199254740992
      && nVal < 9007199254740992
      && Math.floor(nVal) === nVal;
  };
}