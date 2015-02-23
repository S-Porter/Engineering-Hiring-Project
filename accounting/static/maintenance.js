"use strict";
    
$(function() {
    $( "#submit_payment_button" ).click(validate_and_submit_payment);
    $( "#submit_billing_button" ).click(submit_billing);
    $( "#submit_insured_button" ).click(validate_and_submit_insured);
})

function validate_and_submit_payment() {
    var payment_string = $( "#payment_amount" ).val();
    var payment_amount = +payment_string;
    
    if (isNaN(payment_amount)) {
        $( "#payment_amount" ).val("");
        $( "#submit_error" ).text("The policy number you entered was not recognized, please try again.");
        return;
    }
    payment_amount = parseFloat(payment_amount.toFixed(2));
    
    $( "#submit_error" ).text("");
    $.post($SCRIPT_ROOT + "/payment/",
        {
            id: $( "#id" ).val(),
            payment_amount: $( "#payment_amount").val()
        },
        function(result) {
            $( "#submit_success" ).text(result);
            $( "#payment_amount").val("")
        });
}

function submit_billing() {
    $.post($SCRIPT_ROOT + "/billing/",
        {
            id: $( "#id" ).val(),
            new_billing: $( "#new_billing").val()
        },
        function(result) {
            $( "#submit_success" ).text(result);
        });
}

function validate_and_submit_insured() {
    var new_insured = $( "#new_insured" ).val();
    if (new_insured == "") {
        return
    }

    var reg = /^\d/;
    if (new_insured.match(reg)) {
        $( "#submit_error" ).text("You cannot have a named-insured that starts with a number.");
        return;
    }
    $( "#submit_error" ).text("");
    $.post($SCRIPT_ROOT + "/insured/",
        {
            id: $( "#id" ).val(),
            new_insured: $( "#new_insured").val()
        },
        function(result) {
            $( "#submit_success" ).text(result.text);
            $( "#named_insured" ).text(result.name);
            $( "#new_insured" ).val("");
        });
}