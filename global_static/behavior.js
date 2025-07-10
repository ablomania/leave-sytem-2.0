

function dateReminder(startDate, daysRequested) {
    if(startDate == null || startDate == "" || startDate == undefined) {
        console.log("Start date is null or empty");
    } else {
        calcEndDate(startDate, daysRequested);
    }
}

function calcEndDate(startDate, daysRequested) {
    let totalDays = 0;
    let validDays = 0; // Count of weekdays (Monday to Friday)
    let currentDate = new Date(startDate); // Clone the start date to avoid modifying the original
    startDate = new Date(startDate); // Ensure `startDate` is a Date object

    if(document.getElementById("end_date_text")) {
        document.getElementById("end_date_text").remove();
    }

    // Remove any existing error message for `startDateError`
    let startDateError = document.getElementById("startDateError");
    if (startDateError) {
        startDateError.remove();
    }

    // Validation: Ensure `daysRequested` is greater than 0
    if (daysRequested <= 0) {
        let errorNode = document.createElement("p");
        errorNode.id = "startDateError";
        let errorMessage = document.createTextNode("Please select a valid number of days.");
        errorNode.appendChild(errorMessage);
        document.getElementById("start_date_container").appendChild(errorNode);
        return;
    }

    // Validation: Ensure `startDate` is a weekday (Monday to Friday)
    if (startDate.getDay() === 0 || startDate.getDay() === 6) {
        let errorNode = document.createElement("p");
        errorNode.id = "startDateError";
        let errorMessage = document.createTextNode("Please select a weekday as the start date.");
        errorNode.appendChild(errorMessage);
        document.getElementById("start_date_container").appendChild(errorNode);
        return;
    }

    // Validation: Ensure `startDate` is a future date
    let today = new Date();
    today.setHours(0, 0, 0, 0); // Normalize today's date to midnight
    if (startDate < today) {
        let errorNode = document.createElement("p");
        errorNode.id = "startDateError";
        let errorMessage = document.createTextNode("Please select a future date as the start date.");
        errorNode.appendChild(errorMessage);
        document.getElementById("start_date_container").appendChild(errorNode);
        return;
    }

    // Loop to calculate the end date
    while (validDays < daysRequested-1) {
        currentDate.setDate(currentDate.getDate() + 1); // Move to the next day

        // Check if it's a weekday (Monday to Friday: 1 to 5)
        if (currentDate.getDay() > 0 && currentDate.getDay() < 6) {
            validDays++; // Increment valid weekdays
        }
        totalDays++; // Increment total days (including weekends)
    }

    if(document.getElementById("end_date_text")) {
        document.getElementById("end_date_text").remove();
    }
    let resultNode = document.createElement("p");
    resultNode.id = "end_date_text";
    let resultMessage = document.createTextNode("End Date: " + currentDate.toDateString());
    resultNode.appendChild(resultMessage);
    document.getElementById("end_date").appendChild(resultNode);
    document.getElementById("end_date_input").value = currentDate.toISOString().split('T')[0]; // Set the value of the end date input
    document.getElementById("resumption_date").value = currentDate.toISOString().split('T')[0];// Set the value of the resumption date input
}

function changeDays(daysRequested, startDateValue, endDateValue, daysChanged) {
    // Check if the change_days flag is true or false
    if(daysChanged == "true") {
        document.getElementById("days_requested").disabled = false; // Enable the days_requested input
        document.getElementById("start_date").disabled = false;
        document.getElementById("change_days").value =  false;
        document.getElementById("days_requested_label").style.color = "#333";
        document.getElementById("start_date_label").style.color = "#333";
    } else {
        document.getElementById("change_days").value = true; // Set the change_days flag to true
        document.getElementById("days_requested").disabled = true; // Disable the days_requested input
        document.getElementById("days_requested").value = daysRequested; // Set the value of days_requested to the previous value
        document.getElementById("start_date").disabled = true;
        document.getElementById("start_date").value = startDateValue; // Set the value of start_date to the previous value
        document.getElementById("end_date_input").value = endDateValue; // Set the value of end_date_input to the previous value
        document.getElementById("days_requested_label").style.color = "gray"; // Change the color of the label to gray
        document.getElementById("start_date_label").style.color = "gray"; // Change the color of the label to gray
    }
}

function enableField() {
    // Enable the days_requested input field
    document.getElementById("days_requested").disabled = false;
    document.getElementById("start_date").disabled = false; // Enable the start_date input field
}

window.onload = function dd() {
    if(document.querySelector(".leave-request-container")) {
        let someValue = document.getElementById("leave_type_id").value;
        document.getElementById("leave_type").value = someValue;
    }
    if(document.getElementById("start_date")) {
        startDate = document.getElementById("start_date").value;
        daysRequested = document.getElementById("days_requested").value;
        calcEndDate(startDate, daysRequested);
    }
    if(document.getElementById("user_type")) {
        user_type = document.getElementById("user_type").value
        departmentId = document.getElementById("user_department_id").value
        customizePage(user_type, departmentId)
    }
    if(document.getElementById("id_email") && document.getElementById("id_password1")) {
        editFields()
    }
    if(document.getElementById("id_username") && document.getElementById("id_password")) {
        const usernameField = document.getElementById("id_username");
        const password = document.getElementById("id_password");
        let loginList  = new Array(usernameField, password);
        loginList.forEach((e) => {
            e.style.width = "230px";
            e.style.height ="30px";
            e.style.borderRadius = "5px";
            e.style.border = "1px gray solid";
        })
    }
    if(document.getElementById("password_reset_page") && document.getElementById("code_label")) {
        someFunction();
    }
    let inputs = document.getElementsByTagName('input');
    Array.from(inputs).forEach(input => {
        input.addEventListener('change', function() {
            if(document.querySelector(".phone_error")) {
                document.querySelector(".phone_error").remove(); // Remove the previous error message if it exists
                console.log("removed")
            }
            let errorNode = document.createElement("p");
            errorNode.className = "phone_error";
            errorNode.id = "phone_error";
            let errorMessage = document.createTextNode("Please enter a valid phone number without letters.");
            errorNode.appendChild(errorMessage);
            errorNode.style.color = "red";

            let sButton = document.getElementById("submit-button")
            let interupt = true;

            // Remove all double quotation marks
            // Remove all single quotation marks
            if (input.value.includes("'")) {
                input.value = input.value.replace(/'/g, ""); // Global replacement
                console.log(input.value); // Log the updated value
            }
            if (input.value.includes('"')) {
                input.value = input.value.replace(/"/g, ""); // Global replacement
                console.log(input.value); // Log the updated value
            } else {
                sButton.disabled = false; // Enable the submit button
            }
            if (input.id == "phone_number" || input.id == "id_phone_number" || input.id == "phone") {
                let regex = /[a-zA-Z]/; // Matches any letter (uppercase or lowercase)
                if (input.value.length > 14) {
                    errorMessage.textContent = "Please enter a valid phone number with at most 14 digits.";
                    errorNode.appendChild(errorMessage);
                    input.parentNode.parentNode.insertBefore(errorNode, input.parentNode.parentNode.children[0]);
                    sButton.disabled = true; // Disable the submit button
                    interupt = false;
                    console.log("aaa", sButton.disabled)
                } else if (input.value.length <= 14 && input.value.length >= 10) {
                    sButton.disabled = false;
                }
                if(input.value.length < 10) {
                    errorMessage.textContent = "Please enter a valid phone number with at least 10 digits.";
                    errorNode.appendChild(errorMessage);
                    input.parentNode.parentNode.insertBefore(errorNode, input.parentNode.parentNode.children[0]);
                    sButton.disabled = true; // Disable the submit button
                    interupt = false;
                } else if(input.value.length == 10) {
                    sButton.disabled = false;
                }
                if (regex.test(input.value)) {
                    // input.value = input.value.replace(/[a-zA-Z]/g, ""); // Remove letters
                    input.parentNode.parentNode.insertBefore(errorNode, input.parentNode.parentNode.children[0]);
                    console.log("The string contains a letter.");
                    sButton.disabled = true; // Disable the submit button
                    interupt = true;
                } else if(!regex.test(input.value) && interupt) {
                    sButton.disabled = false; // Enable the submit button
                    console.log("The string does not contain any letters.");
                }
            } if(sButton.disabled == false) {
                sButton.style.backgroundColor = "#00a400"; // Green background color
                sButton.style.color = "white"; // White text color
            }
            else if(sButton.disabled == true) {
                sButton.style.backgroundColor = "gray"; // Gray background color
                sButton.style.color = "white"; // White text color
            }
        });
    });
} 

function someFunction() {
    let link_reload = document.getElementById("link_reload");
    let code_instructions = document.getElementById("code_instructions")
    let code = document.getElementById("verification_code");
    let code_label = document.getElementById("code_label");
    let minute = Number(document.getElementById("minute").textContent);
    let seconds = Number(document.getElementById("seconds").textContent);
    const timerInterval = setInterval(() => {
        console.clear()
        my_time = countdownPassword(minute, seconds);
        minute = my_time[0];
        seconds = my_time[1];
        console.log( minute," : ", seconds);
        console.log("s", seconds);
        document.getElementById("minute").textContent = minute;
        document.getElementById("seconds").textContent = seconds;
        if(minute == 0  && seconds == 0) {
            clearInterval(timerInterval);   
            code.style.display = "none";
            code_label.textContent = textContent = "Verification code expired. Please refresh the page, choose 'yes' or 'continue' if asked to resubmit form";
            code_instructions.remove();  
            document.getElementById("countdown-wrapper").remove();
        }
    }, 1000);
}

function countdownPassword(minute, seconds) {
    seconds = seconds - 1;
    if(seconds < 1 && minute > 0) {
        minute = minute - 1;
        seconds = 59;
    }
    else if(seconds < 1 && minute < 1) {
        minute = 0;
        seconds = 0;
    }
    return [minute, seconds];
    
}

function editFields() {
    const emailField = document.getElementById("id_email");
    const passwordField1 = document.getElementById("id_password1");
    const passwordField2 = document.getElementById("id_password2");
    const department = document.getElementById("id_department");
    const type = document.getElementById("id_type");
    otherList = new Array(department, type)
    const list = new Array(emailField, passwordField1, passwordField2)
    list.forEach((e) => {
        e.style.borderRadius = "5px";
        e.style.height = "30px";
        e.style.border = "1px gray solid";
        e.style.width = "455px";
        e.style.color = "#333";
        e.style.marginBottom = "10px";
    })
    otherList.forEach((e) => {
        e.style.width = "460px";
        e.style.color = "#333";
        e.style.marginBottom = "10px";
    })
    passwordField1.addEventListener("change", function() {
        checkPassword();
    })    
    passwordField2.addEventListener("change", function() {
        checkPassword();
    })
}
function checkPassword() {
    if(document.getElementById("newNode")) {
        document.getElementById("newNode").remove();
    }
    password1 = document.getElementById("id_password1").value;
    password2 = document.getElementById("id_password2").value;
    let password2wrapper = document.getElementById("user_type");
    const all = document.querySelectorAll(".field_wrapper");
    for(let i=all.length-1; i >= 0; i--) {
        let v = all[i].childNodes
        for(let j=v.length-1; j >= 0; j--) {
            let u = v[j].childNodes
            for(let q=u.length-1; q >= 0; q--) {
                if(u[q].id == "id_password2") {
                    password2wrapper = u[q].parentNode;
                    break;
                }
            }
        }
    }
    if(password1 != '' && password2 != '') {
        if(password1 == password2) {
            let newNode = document.createElement("p");
            newNode.id = "newNode";
            let textNode = document.createTextNode("Passwords match. 😀");
            newNode.appendChild(textNode);
            password2wrapper.appendChild(newNode);
            password2wrapper.style.marginBottom = "10px";
            newNode.style.color = "green";
        }
        else if(password1 != password2) {
            document.createElement("p");
            let newNode = document.createElement("p");
            newNode.id = "newNode";
            let textNode = document.createTextNode("Passwords do not match. 🙁")
            newNode.appendChild(textNode);
            password2wrapper.appendChild(newNode);
            password2wrapper.style.marginBottom = "10px";
            newNode.style.color = "red";
        }
    }
    
}

function showMePassword(someValue, password1Id, password2Id) {
    password1 = document.getElementById(password1Id);
    password2 = document.getElementById(password2Id);
    if((someValue == "true" && password1.type == "password") || (someValue == "true" && password2.type == "password")) {
            password1.type = "text";
            password2.type = "text";
        }
    else {
        password1.type = "password";
        password2.type = "password";
    }
}

function showMePassword2(someValue, password1Id) {
    password1 = document.getElementById(password1Id);
    if((someValue == "true" && password1.type == "password")) {
            password1.type = "text";
        }
    else {
        password1.type = "password";
    }
}

function sortTable(columnIndex) {
    const table = document.getElementById("staffTable");
    const rows = Array.from(table.rows).slice(1); // Exclude the header row
    let isAscending = table.getAttribute(`data-sort-${columnIndex}`) === "asc";
    table.setAttribute(`data-sort-${columnIndex}`, isAscending ? "desc" : "asc");

    rows.sort((a, b) => {
        const cellA = a.cells[columnIndex].textContent.trim();
        const cellB = b.cells[columnIndex].textContent.trim();

        return isAscending
            ? cellA.localeCompare(cellB)
            : cellB.localeCompare(cellA);
    });

    // Reorder rows
    rows.forEach(row => table.tBodies[0].appendChild(row));
}

function submitMyForm() {
    let myform = document.getElementById("staff_detais_form");
    myform.submit();
}

function customizePage(user_type, departmentId) {
    if(user_type == 'HOD') {
        const department = document.getElementById('id_department');
        if(department) {
            for(let i=department.options.length-1; i >= 0; i--) {
                if(department.options[i].value != departmentId) {
                    department.options.remove(i)
                }
            }
        }
    }
    const staffType = document.getElementById("id_type")
        if(staffType) {
            for(let i=staffType.options.length-1; i >= 0; i--) {
                if(staffType.options[i].value == user_type) {
                    staffType.options.remove(i)
                }
                else if(staffType.options[i].value === "ADMIN" && user_type === "HOD") {
                    staffType.options.remove(i)
                }
                else if(staffType.options[i].value == "SUPER_ADMIN" && user_type == "HOD") {
                    staffType.options.remove(i)
                }
                else if(staffType.options[i].value == "SUPER_ADMIN" && user_type == "ADMIN") {
                    staffType.options.remove(i)
                }
            }
        }
}

function comparePasswords(password1, password2) {
    console.log("p1 : ", password1)
    console.log("p2 : ", password2)
    if(document.getElementById("newNode")) {
        document.getElementById("newNode").remove()
    }
    let newNode = document.createElement("p");
    newNode.id = "newNode";
    
    
    if(password1 != '' && password2 != ''){
        if(password1 != password2){
            let textNode = document.createTextNode("Passwords do not match. 🙁");
            newNode.appendChild(textNode);
            passwordError = document.getElementById("passwordError");
            passwordError.appendChild(newNode);
        }
        else {
            let textNode = document.createTextNode("Passwords match! 😀");
            newNode.appendChild(textNode);
            passwordError = document.getElementById("passwordError");
            passwordError.appendChild(newNode);
            passwordError.appendChild(newNode);
        }
    }
}

function submitMyForm2() {
    if(document.getElementById("department_details_form")) {
        let myForm = document.getElementById("department_details_form");
        myForm.submit();
    }
}

function closeUp() {
    if(document.querySelector(".inner123")) {
        console.log("found")
        let node = document.querySelector(".inner123").className = "inner1234";
        
            
    } else{
        console.log("not found")
    }
}

function editDepartment() {
    if(document.querySelector(".popup0")) {
        let myEdit = document.querySelector(".popup0");
        myEdit.className = "popup";
        document.getElementById("edit").style.display = "flex";
    }
    else if(document.querySelector(".popup")) {
        let myEdit = document.querySelector(".popup");
        myEdit.className = "popup0";
        document.getElementById("edit").style.display = "none";
    }
}

function showList(someEvent, departmentName, departmentId, slug, myURL, count) {
    if(document.querySelectorAll(".inner123")) {
        document.querySelectorAll(".inner123").forEach((e) => {
            e.remove();
        });
    }
    console.log("uu", myURL)
    let nodeName = "inner-" + count;
    let inner123 = document.getElementById(nodeName);

    // Safely toggle grid classes and apply changes
    if (inner123) {
        // Handle overview element
        inner123.className = "inner123";
    } else {
        console.error("Inner grid element not found!");
    }
    linkName = "myLink" + count;
    let myLink = document.getElementById(linkName);
    myLink.href = myURL;
}

function deleteDepartment() {
    if(document.querySelector(".popup1")) {
        let node = document.querySelector(".popup1");
        node.className = "popup2";
    }
    else if(document.querySelector(".popup2")) {
        let node = document.querySelector(".popup2");
        node.className = "popup1";
    }
}

function deleteVariant(someEvent, someValue) {
    console.log("vv", someValue)
    let box1 = document.getElementById("reassign");
    let box2 = document.getElementById("set_to_none");
    let box3 = document.getElementById("delete_all");
    
    let node1 = document.querySelector(".reassign-wrapper");
    let node2 = document.querySelector(".set_to_null-wrapper")
    let node3 = document.querySelector(".delete_all-wrapper")

    let someTarget = someEvent.target;
    let myForm = document.getElementById("delete-department-form");
    myForm.reset();
    someTarget.value = someValue;
    someTarget.checked = true;
    if(someTarget == box1 && someValue == "reassign") {
        node1.style.display = "flex";
        node2.style.display = "none";
        node3.style.display = "none";
    }
    else if(someTarget == box2 && someValue == "set_to_none") {
        node1.style.display = "none";
        node2.style.display = "flex";
        node3.style.display = "none";
    }
    else if(someTarget == box3 && someValue == "delete_all") {
        node1.style.display = "none";
        node2.style.display = "none";
        node3.style.display = "flex";
    }
    
}

function changeDetails() {
    let node1  = document.querySelector(".staff-details-forms-wrapper");
    let node2 = document.querySelector(".left");
    let node3 = document.querySelector(".containerz");
    let changeButton = document.querySelector(".change-button");
    
    if(node2.style.display != "none") {
        node2.style.display = "none";
        node1.style.display = "flex";
        node3.style.justifyContent = "center";
        node3.style.display = "flex";
        node3.style.flexDirection = "column";
        changeButton.textContent = "Back to Details";
    }
    else if(node2.style.display == "none") {
        node2.style.display = "flex";
        node1.style.display = "none";
        node3.style.justifyContent = "space-between";
        node3.style.display = "flex";
        node3.style.flexDirection = "row";
        changeButton.textContent = "Change Details";
    }
}

function setDaysEligible(someValue, daysEligible) {
    let daysEligibleField = document.getElementById("days_eligible");
    let daysEntitledField = document.getElementById("days_entitled");
    someValue = Number(someValue);
    daysEligible = Number(daysEligible);
    const numbers = Array.from({ length: someValue }, (_, i) => i + 1);
    for(let i = daysEligibleField.options.length - 1; i >= 0; i--) {
        daysEligibleField.options.remove(i);
    }
    for(let i=0; i < numbers.length; i++) {
        if(numbers[i] == daysEligible) {
            daysEligibleField.options[i] = new Option(numbers[i], numbers[i], true, true);
        } else {
            daysEligibleField.options[i] = new Option(numbers[i], numbers[i], false, false);
        }
    }
    
}

function loadConfirmer(action) {
    let yesButton = document.getElementById("yes-button");
    let noButton = document.getElementById("no-button");    
    let confirmNode = document.querySelector(".confirmer");
    let confirmMessage = document.querySelector(".confirm-message");
    confirmNode.style.display = "flex";
    let myForm = document.getElementById("staff-details-form");
    if(action == 1) {
        confirmMessage.textContent = "Are you sure you want to change the details of this staff member? This action cannot be undone.";
    }
    else if(action == 2) {
        myForm = document.getElementById("staff-delete-form");
        confirmMessage.textContent = "Are you sure you want to delete this staff member? This action cannot be undone.";
    }
    else if(action == 3) {
        myForm = document.getElementById("password-reset-form");
        confirmMessage.textContent = "Are you sure you want to reset the password of this staff member? This action cannot be undone. A password reset request email will be sent to the staff's email address";
    }
    yesButton.addEventListener("click", function() {
        confirmNode.style.display = "none";
        myForm.submit();
    })
    noButton.addEventListener("click", function() {
        confirmNode.style.display = "none";
    })
}

function expandMenu(someEvent, number) {
    let targetParent = someEvent.target.parentNode;
    let nodeName = "leave-requests-grid" + number;
    let node = document.getElementById(nodeName)
    let nodeParent = node.parentNode
    if(targetParent === nodeParent) {
        if(node.className == "invisible") {
            node.className = "leave-requests-grid";
        }
        else if(node.className == "leave-requests-grid") {
            node.className = "invisible";
        }
    }
}

function showMyTable(tableId) {
    if(document.querySelector(".dept-grid-inner1")) {
        document.querySelector(".dept-grid-inner1").className = "dept-grid-inner";
    }
    let tableName = "dept-grid-inner" + tableId;
    let table = document.getElementById(tableName);
    if(table.className != "dept-grid-inner1") {
        table.className = "dept-grid-inner1";
    }
    else if(table.className == "dept-grid-inner1") {
        table.className = "dept-grid-inner";
    }
}
const closeMyPopup = (count) => {
    let tableName = "dept-grid-inner" + count;
    let table = document.getElementById(tableName);
    table.className = "dept-grid-inner";
}

const expandList = (count) => {
    let tableName = "dept-grid-inner__" + count;
    console.log("count", count)
    let table = document.getElementById(tableName);
    let headName = "table-header__" + count;
    console.log("headname", headName)
    let tableHead = document.getElementById(headName);
    console.log("table", table)
    console.log("tablehead", tableHead)
    if(table.className == "dept-grid-inner") {
        console.log("table i", table)
        table.className = "dept-grid-inner-2";
        tableHead.className = "table-header";
    }
    else if(table.className == "dept-grid-inner-2") {
        console.log("table i2", table)
        table.className = "dept-grid-inner";
        tableHead.className = "table-header1";
    }
}

const loadLeave = (someValue) => {
    console.log(someValue)
    let node = null
    let leaveList = ["Annual Leave", "Casual Leave", "Sick Leave", "Maternity Leave", "Compassionate Leave", "Disembarkation Leave", "Study Leave With Pay", "Study Leave Without Pay", "Leave Without Pay", "Other"];
    let leaveHeader = document.querySelector(".leave1-header");
    let leaveDetails = document.querySelector(".leave1-details");
    let reasonField = document.getElementById("reason");
    let reasonLabel = document.getElementById("reason-label");
    let disContainer = document.getElementById("dis-container");
    let medContainer = document.getElementById("med-note-container");
    let instContainer = document.getElementById("institution-container");
    let courseContainer = document.getElementById("course-container");
    let letContainer = document.getElementById("letter-container");
    let matDueDate = document.getElementById("m-due-date");
    nodeList = [leaveDetails, reasonField, reasonLabel]
    leaveHeader.textContent = leaveList[someValue-1];
    if(someValue != 1) {
        nodeList.forEach((e) => {
            if(someValue != 4 && e == reasonField) {
                e.style.display = "block";
            }
            else if(someValue != 4 && e == reasonLabel) {
                e.style.display = "block";
            }
            else {
                e.style.display = "none";
            }
        })
    }else{
        nodeList.forEach((e) => {
            if(e == leaveDetails) {
                e.style.display = "grid";
            } else{
                e.style.display = "block";
            }
        })
    }
    if(someValue == 6) {
        disContainer.style.display = "flex";
    } else {
        disContainer.style.display = "none";
        document.getElementById("disembarkation").value = null;
    }
    if(someValue == 3) {
        medContainer.style.display = "flex";
    } else {
        medContainer.style.display = "none";
        document.getElementById("med-note").value = null
    }
    if(someValue == 7 || someValue == 8) {
        instContainer.style.display = "flex";
        courseContainer.style.display = "flex";
        letContainer.style.display = "flex";
    } else {
        instContainer.style.display = "none";
        courseContainer.style.display = "none";
        letContainer.style.display = "none";
        document.getElementById("course").value = null;
        document.getElementById("institution").value = null;
        document.getElementById("letter").value = null;
    }
    if(someValue == 4) {
        matDueDate.style.display = "flex";
    } else {
        matDueDate.style.display = "none";
        document.getElementById("due-date").value = null;
    }
    if(someValue == 1) {
        document.getElementById("disembarkation").value = null;
        document.getElementById("med-note").value = null;
        document.getElementById("course").value = null;
        document.getElementById("institution").value = null;
        document.getElementById("letter").value = null;
        document.getElementById("due-date").value = null;
    }
    let someIndex = leaveList[someValue-1]
    console.log(someIndex)
    document.getElementById("leave_type").value = someValue;
}

// const compareUsernames = (someEvent, someValue, usernames) => {
//     if(document.getElementById("username-error")) {
//         document.getElementById("username-error").remove(); // Remove the previous error message if it exists
//     }
//     let parent = document.querySelector(".sign_up_form");
//     let errorNode = document.createElement("p");
//     errorNode.className = "username-error";
//     errorNode.id = "username-error";
//     let errorMessage = document.createTextNode("");
//     errorNode.appendChild(errorMessage);
//     if(usernames.includes("\"") || usernames.includes("\[") || usernames.includes("\]") || usernames.includes("\'")) {
//         usernames = usernames.replace(/"/g, ""); // Global replacement
//         usernames = usernames.replace(/\[/g, ""); // Global replacement
//         usernames = usernames.replace(/\]/g, ""); // Global replacement
//         usernames = usernames.replace(/'/g, ""); // Global replacement
//     }
//     userArray = usernames.split(", ");
//     userArray.forEach((e) => {
//         if (e.toLowerCase() == someValue.toLowerCase()) {
//             errorMessage.textContent = "This username already exists. Please choose a different username.";
//             errorNode.appendChild(errorMessage);
//             errorNode.style.color = "red";
//             parent.insertBefore(errorNode, parent.children[0]);
//         }
//     })
// }

