function ActivateCustomer(idno)
{

    var dataToSend = {
            IDNo: idno,
            ActionTag: 'ActivateCustomer',
            // Include any other necessary data from the form
            // For example:
            // otherField: $('#otherFieldId').val()
        };

    var csrf = GetInputValue("hdncsrf");
    showBusyPopup();
    $.ajax({
        type: "POST",
        url: "/Customers/",
        data: dataToSend,
        success: function(response,request) {
            hideBusyPopup();
            LoadCollabSuccess(response.Success['details']);
            
            setTimeout(function() {
                location.reload();
                }, 3000);
            
        },
        error: function(request) {
            var ErrJson = JSON.parse(request.responseText);
            hideBusyPopup();
            if(request.status === 404)
                LoadCollabError(ErrJson.Exception);
            else
                LoadCollabInfo(ErrJson.Exception);

        }
    });
    hidePleaseWait();
}

function ResetPassword(idno)
{

    var dataToSend = {
            IDNo: idno,
            ActionTag: 'ResetPassword', 
            // Include any other necessary data from the form
            // For example:
            // otherField: $('#otherFieldId').val()
        };

    var csrf = GetInputValue("hdncsrf");
    showBusyPopup();
    $.ajax({
        type: "POST",
        url: "/Customers/",
        data: dataToSend,
        success: function(response,request) {
            hideBusyPopup();
            LoadCollabSuccess(response.Success['details']);
            
            setTimeout(function() {
                location.reload();
                }, 2000);
            
        },
        error: function(request) {
            var ErrJson = JSON.parse(request.responseText);
            hideBusyPopup();
            if(request.status === 404)
                LoadCollabError(ErrJson.Exception);
            else
                LoadCollabInfo(ErrJson.Exception);

        }
    });
    hidePleaseWait();
}