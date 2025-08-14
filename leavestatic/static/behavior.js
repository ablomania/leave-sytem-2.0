const paginationConfig = {
    groups: { selector: ".groups .group_item", perPage: 10 },
    staff_all: { selector: "#staff_all .staff_card", perPage: 10 },
    gpd: { selector: ".gpd .staff_item", perPage: 10 },
    app356: { selector: ".app356 .approver-item", perPage: 8 },
    genders: { selector: ".genders .gender-card", perPage: 8 },
    leave_types: { selector: ".leave_types .lvtlb", perPage: 5 },
    holidays: { selector: ".holidays .vholitem, .holidays .fholitem", perPage: 5 },
    levels: { selector: ".levels .level-card", perPage: 10 },
    categories: { selector: ".categories .gender-card", perPage: 10 }
};

const sectionState = {};

function initPagination(sectionName) {
    const config = paginationConfig[sectionName];
    if (!config) return;

    const cards = document.querySelectorAll(config.selector);
    if (cards.length <= config.perPage) return;

    sectionState[sectionName] = { page: 1, cards, totalPages: Math.ceil(cards.length / config.perPage) };

    const bar = document.querySelector(`.pagination-bar[data-section="${sectionName}"]`);
    if (bar) {
        bar.innerHTML = `
        <button onclick="changePage('${sectionName}', -1)">« Prev</button>
        <span id="${sectionName}_page_info"></span>
        <button onclick="changePage('${sectionName}', 1)">Next »</button>
        `;
        bar.style.display = "flex";
    }

    renderPage(sectionName);
}

function renderPage(sectionName) {
    const { page, cards, perPage, totalPages } = {
        ...sectionState[sectionName],
        perPage: paginationConfig[sectionName].perPage
    };

    cards.forEach((card, i) => {
        card.style.display = (i >= (page - 1) * perPage && i < page * perPage) ? "block" : "none";
    });

    const info = document.getElementById(`${sectionName}_page_info`);
    if (info) info.textContent = `Page ${page} of ${totalPages}`;
    }

    function changePage(sectionName, delta) {
    const state = sectionState[sectionName];
    if (!state) return;

    state.page += delta;
    if (state.page < 1) state.page = 1;
    if (state.page > state.totalPages) state.page = state.totalPages;

    renderPage(sectionName);
}

document.addEventListener("DOMContentLoaded", () => {
    Object.keys(paginationConfig).forEach(initPagination);
});



function selAllBoxes(boxState, boxClassName) {
    let checkboxes = document.querySelectorAll(`.${boxClassName}`);
    let count = 0;
    checkboxes.forEach((checkbox) => {
        checkbox.checked = boxState ? true: false; // Toggle the checked state
    });
    checkboxes.forEach((checkbox) => {
        if(checkbox.checked) {
            count++;
        }
    });
    if(count == 0) {
        document.querySelector('.mid').style.display = "none";
    } else {
        document.querySelector(`.count_selected`).textContent = count;
    }
}

function selectCheckBox(boxClassName, multiSelBoxClassName) {
    let checkboxes = document.querySelectorAll(`.${boxClassName}`);
    let multiSelCheckbox = document.querySelector(`.${multiSelBoxClassName}`);
    let count = 0;
    checkboxes.forEach((checkbox) => {
        if(checkbox.checked) {
            count++;
        }
    });
    if(count === checkboxes.length) {
        multiSelCheckbox.checked = true; // Check the multi-select checkbox
    } else {
        multiSelCheckbox.checked = false; // Uncheck the multi-select checkbox
    }
}

function displayMid(midClassName) {
    let midElement = document.querySelector(`.${midClassName}`);
    if(midElement) {
        midElement.style.display = "flex"; // Show the mid element
    } else {
        console.error(`Element with class ${midClassName} not found.`);
    }
}

function hideMid(midClassName) {
    let midElement = document.querySelector(`.${midClassName}`);    
    if(midElement) {
        midElement.style.display = "none"; // Hide the mid element
    } else {    
        console.error(`Element with class ${midClassName} not found.`);
    }
}



function updateCounter(counterClassName, checkBoxClassName) {
    let counterElement = document.querySelector("."+counterClassName);
    if(counterElement) {
        let checkboxes = document.querySelectorAll(`.${checkBoxClassName}`);
        let count = 0;
        checkboxes.forEach((checkbox) => {
            if(checkbox.checked) {
                count++;
            }
        });
        counterElement.textContent = count; // Update the counter text
    } else {
        console.error(`Counter element with class ${counterClassName} not found.`);
    }
}

function resetCounter(counterClassName) {
    let counterElement = document.querySelector("."+counterClassName);
    if(counterElement) {
        counterElement.textContent = "0"; // Reset the counter text to 0
    } else {
        console.error(`Counter element with class ${counterClassName} not found.`);
    }
}

function resetAndHideGroupSelect(groupSelectId) {
    let groupSelect = document.getElementById(groupSelectId);
    if(groupSelect) {
        groupSelect.style.display = "none"; // Hide the group select dropdown
        groupSelect.required = false; // Make it not required
        groupSelect.disabled = true; // Disable the group select dropdown
    } else {
        console.error(`Group select element with ID ${groupSelectId} not found.`);
    }
}

function resetForm(formId) {
    let form = document.getElementById(formId);
    if(form) {
        form.reset(); // Reset the form fields
    }
}

function toggleGroupSelect(value, groupSelectId) {
    let groupSelect = document.getElementById(groupSelectId);
    if(groupSelect) {
        if(value === "change_group" || value === "change_group_group" || value === "change_category") {
            groupSelect.style.display = "block"; // Show the group select dropdown
            groupSelect.required = true; // Make it required
            groupSelect.disabled = false; // Enable the group select dropdown
            groupSelect.focus(); // Set focus to the group select dropdown
        } else {
            groupSelect.style.display = "none"; // Hide the group select dropdown
            groupSelect.required = false; // Make it not required
            groupSelect.disabled = true; // Disable the group select dropdown
        }
    } else {
        console.error(`Group select element with ID ${groupSelectId} not found.`);
    }
}








function dateReminder(startDate, daysRequested) {
    if(startDate == null || startDate == "" || startDate == undefined) {
        console.log("Start date is null or empty");
    } else {
        calcEndDate(startDate, daysRequested, all_holidays);
    }
}



function calcEndDate(startDate, daysRequested) {
    if (document.getElementById("startDateError")) {
        document.getElementById("startDateError").remove();
    }
    if (daysRequested <= 0) {
        return displayError("Please select a valid number of days.");
    }
    console.log(all_holidays)
    
    console.log("dd", new Date(all_holidays[0]))
    let currentDate = new Date(startDate);
    const statHdateList = all_holidays.map(dateStr => new Date(dateStr));

    // const statHdateList = [
    //     new Date(2025, 0, 1), new Date(2025, 0, 7), new Date(2025, 2, 6),
    //     new Date(2025, 3, 18), new Date(2025, 3, 21), new Date(2025, 4, 1),
    //     new Date(2025, 4, 25), new Date(2025, 7, 4), new Date(2025, 8, 21),
    //     new Date(2025, 11, 5), new Date(2025, 11, 25), new Date(2025, 11, 26)
    // ];

    if (!isValidStartDate(currentDate, statHdateList)) {
        return;
    }

    let validDays = 0;
    while (validDays < daysRequested - 1) {
        currentDate.setDate(currentDate.getDate() + 1);
        if (isValidWorkday(currentDate, statHdateList)) {
            validDays++;
        }
    }

    updateEndDateUI(currentDate);
}

function displayError(message) {
    let errorNode = document.createElement("p");
    errorNode.id = "startDateError";
    errorNode.textContent = message;
    document.getElementById("start_date_container").appendChild(errorNode);
}

function isValidStartDate(date, holidayList) {
    let today = new Date();
    today.setHours(0, 0, 0, 0);

    if (date < today) {
        displayError("Please select a future date as the start date.");
        return false;
    }
    if (date.getDay() === 0 || date.getDay() === 6) {
        displayError("Please select a weekday as the start date.");
        return false;
    }
    if (holidayList.some(holiday => holiday.toDateString() === date.toDateString())) {
        displayError("Holidays not allowed. Please select a working day as the start date.");
        return false;
    }

    return true;
}

function isValidWorkday(date, holidayList) {
    return date.getDay() > 0 && date.getDay() < 6 && !holidayList.some(holiday => holiday.toDateString() === date.toDateString());
}

function updateEndDateUI(date) {
    if (document.getElementById("end_date_text")) {
        document.getElementById("end_date_text").remove();
    }

    let resultNode = document.createElement("p");
    resultNode.id = "end_date_text";
    resultNode.textContent = "End Date: " + date.toDateString();

    document.getElementById("end_date").appendChild(resultNode);
    document.getElementById("end_date_input").value = date.toISOString().split('T')[0];
    document.getElementById("resumption_date").value = date.toISOString().split('T')[0];
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
    let deviceHeight = window.screen.height;
    document.querySelector(".body").style.minHeight = deviceHeight + "px";
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

    


    let screenWidth = window.screen.width;
    if(document.getElementById("id_username") && document.getElementById("id_password") && screenWidth > 768) {
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
                    document.querySelector(".errorNode").appendChild(errorNode);
                    sButton.disabled = true; // Disable the submit button
                    interupt = false;
                    console.log("aaa", sButton.disabled)
                } else if (input.value.length <= 14 && input.value.length >= 10) {
                    sButton.disabled = false;
                }
                if(input.value.length < 10) {
                    errorMessage.textContent = "Please enter a valid phone number with at least 10 digits.";
                    errorNode.appendChild(errorMessage);
                    document.querySelector(".errorNode").appendChild(errorNode);
                    sButton.disabled = true; // Disable the submit button
                    interupt = false;
                } else if(input.value.length == 10) {
                    sButton.disabled = false;
                }
                if (regex.test(input.value)) {
                    // input.value = input.value.replace(/[a-zA-Z]/g, ""); // Remove letters
                    document.querySelector(".errorNode").appendChild(errorNode);
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

const loadLeave = (someValue ,leaveTypes, staffData) => {
    console.log("CC", leaveTypes)
    console.log("CC1", staffData)
    let leaveType = leaveTypes[someValue]
    let staffLeaveData = staffData[someValue]
    document.getElementById("leave_type").value = someValue;
    // set leave type name
    document.querySelector(".leave1-header").textContent = leaveType.name
    // set days eligible for that type of leave
    document.querySelector(".lvt_days").textContent = leaveType.days;
    // set days taken for that type of leave
    document.querySelector(".lvt_taken").textContent = staffLeaveData.taken;
    // set days remaining
    document.querySelector(".lvt_rem").textContent = staffLeaveData.remaining;
    // set conditionals
    document.querySelector(".request-form").reset();
    document.querySelectorAll(".optional").forEach((e) => {
        e.style.display = "none";
    })
    if(leaveType.i_date == "True") {
        document.getElementById("m-due-date").style.display = "flex";
    } else if (leaveType.i_note == "True") {
        document.getElementById("med-note-container").style.display = "flex";
    } else if (leaveType.i_institution == "True") {
        document.getElementById("institution-container").style.display = "flex";
    } else if (leaveType.i_course == "True") {
        document.getElementById("course-container").style.display = "flex";
    } else if (leaveType.i_letter == "True") {
        document.getElementById("letter-container").style.display = "flex";
    }

    const daysSelect = document.getElementById('days_requested');

    // Clear existing options (optional)
    daysSelect.innerHTML = '';

    // Add a placeholder
    const placeholder = document.createElement('option');
    placeholder.text = '-- Select Days --';
    placeholder.disabled = true;
    placeholder.selected = true;
    daysSelect.appendChild(placeholder);

    // Add actual options (e.g., 1 to 30)
    for (let i = 1; i <= staffLeaveData.remaining; i++) {
        const option = document.createElement('option');
        option.value = i;
        option.text = `${i} day${i > 1 ? 's' : ''}`;
        daysSelect.appendChild(option);
    }
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
            code_label.textContent = textContent = "Verification code expired. Please request a new code.";
            code_instructions.remove();  
            document.getElementById("countdown-wrapper").remove();
            document.getElementById("submit-button").textContent = "Retry";
            document.getElementById("submit-button").addEventListener("click", function() {
                window.location.reload();
            });
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

function reliefReason2(event) {
  const reasonWrapper = document.getElementById("reason_wrapper");
  if (event.target.checked) {
    reasonWrapper.style.display = "flex";
    document.getElementById("reason").required = true;
    document.getElementById("reason").disabled = false;
  } else {
    reasonWrapper.style.display = "none";
    document.getElementById("reason").required = false;
    document.getElementById("reason").disabled = true;
  }
}

function editFields() {
    let screenWidth = window.screen.width;
    console.log("Screen width:", screenWidth);


    const emailField = document.getElementById("id_email");
    const passwordField1 = document.getElementById("id_password1");
    const passwordField2 = document.getElementById("id_password2");
    const department = document.getElementById("id_department");
    const type = document.getElementById("id_type");
    const sex = document.getElementById("id_sex");
    const position = document.getElementById("id_position")
    otherList = new Array(department, type, sex)
    const list = new Array(emailField, position, passwordField1, passwordField2)
    // list.forEach((e) => {
    //     if(screenWidth >= 768){
    //         e.style.borderRadius = "5px";
    //         e.style.height = "30px";
    //         e.style.border = "1px gray solid";
    //         e.style.width = "100%";
    //         e.style.color = "#333";
    //         e.style.marginBottom = "10px";
    //     }
        
    // })
    // otherList.forEach((e) => {
    //     if(screenWidth >= 768){
    //         e.style.width = "100%";
    //         e.style.color = "#333";
    //         e.style.marginBottom = "10px";
    //     }
       
    // })
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
    let screenWidth = window.screen.width;
    if(document.querySelector(".confirmer")) {
        document.querySelector(".confirmer").style.display = "none";
    }
    let yesButton = document.getElementById("yes-button");
    let noButton = document.getElementById("no-button"); 
    let topic = document.getElementById("topic"); 
    let containerz = document.querySelector(".containerz");  
    let confirmNode = document.querySelector(".confirmer");
    let Message = document.querySelector(".confirm-message");
    confirmNode.style.display = "flex";
    let k5 = document.querySelector(".k5");
    let i1 = document.querySelector(".i1");
    let i2 = document.querySelector(".i2");
    let i3 = document.querySelector(".i3");
    let myForm = document.getElementById("staff-details-form");
    
    if(action == 1) {
        confirmMessage.textContent = "Are you sure you want to change the details of this staff member? This action cannot be undone.";
        topic.textContent = "Change Staff Details";
        if(screenWidth < 768) {
            k5.style.backgroundColor = "#ADD8E6";
        }
        i2.style.display = 'block'; // Show the edit icon
        i1.style.display = 'none'; // Hide the delete icon
        i3.style.display = 'none'; // Hide the reset icon
    }
    else if(action == 2) {
        myForm = document.getElementById("staff-delete-form");
        topic.textContent = "Delete Staff Member";
        confirmMessage.textContent = "Are you sure you want to delete this staff member? This action cannot be undone.";
        if(screenWidth < 768) {
            k5.style.backgroundColor = "#FF6347"; // Tomato color for delete action
        }
        i1.style.display = 'block'; // Show the delete icon
        i2.style.display = 'none'; // Hide the edit icon
        i3.style.display = 'none'; // Hide the reset icon
    }
    else if(action == 3) {
        myForm = document.getElementById("password-reset-form");
        topic.textContent = "Reset Staff Password";
        confirmMessage.textContent = "Are you sure you want to reset the password of this staff member? This action cannot be undone. A password reset request email will be sent to the staff's email address";
        if(screenWidth < 768) {
         k5.style.backgroundColor = "#90EE90"; // Light green color for reset action
        }
        i3.style.display = 'block'; // Show the reset icon
        i1.style.display = 'none'; // Hide the delete icon
        i2.style.display = 'none'; // Hide the edit icon
    }
    yesButton.addEventListener("click", function() {
        confirmNode.style.display = "none";
        myForm.submit();
    })
    topic.style.textAlign = "center";
    noButton.addEventListener("click", function() {
        confirmNode.style.display = "none";
    })
}

// function expandMenu(someEvent, number) {
//     let targetParent = someEvent.target.parentNode.parentNode;
//     console.log("pp", targetParent)
//     let nodeName = "leave-requests-grid" + number;
//     let node = document.getElementById(nodeName)
//     let nodeParent = node.parentNode
//     if(targetParent === nodeParent) {
//         if(node.className == "invisible") {
//             node.className = "leave-requests-grid";
//         }
//         else if(node.className == "leave-requests-grid") {
//             node.className = "invisible";
//         }
//     }
// }

function showMyTable(counter) {
    if(document.querySelectorAll('popup-wrapper')) {
        let list = document.querySelectorAll('.popup-wrapper')
        list.forEach((e) => {
            e.style.display = "none";
        })
    }
    let pop = document.getElementById("popup-wrapper" + counter);
    console.log(pop)
    pop.style.display = "flex";
}

const expandList = (counter) => {
    console.log(counter)
    if(document.getElementById("requests-grid" + counter)) {
    node = document.getElementById("requests-grid" + counter);
    if(node.style.display == "grid") {
        node.style.display = "none";
    } else {
        node.style.display = "grid";
    }
    }
}

const closeFunction = (nodeName) => {
    let node = document.getElementById(nodeName);
    node.style.display = "none";
}

const reliefReason = (someEvent) => {
    let node = document.getElementById("reason_wrapper");
    let accept = document.getElementById("relief_ack_accept");
    let deny  = document.getElementById("relief_ack_deny");
    let reason = document.getElementById("reason");
    console.log("mm", deny.checked)
    if(someEvent.target == deny) {
        node.style.display = "flex";
        reason.disabled = false;
    }
    else if(someEvent.target == accept) {
        node.style.display = "none";
        node.value = "";
        reason.disabled = true;
    }
}

const approveReason = (someEvent) => {
    let accept = document.getElementById("approval");
    let deny = document.getElementById("approval2");
    let reason = document.getElementById("reason");
    if(someEvent.target == accept) {
        reason.style.display = "none";
        reason.value = "";
    } else if(someEvent.target == deny) {
        reason.style.display = "flex";
        reason.disabled = false;
        reason.style.border = "1px solid gray";
        reason.style.borderRadius = "5px";
        reason.style.marginTop = "10px";
    }
}






const checkForEmail = (someEvent, someValue, button, emails) => {
    if(document.getElementById("email_error")){
        document.getElementById("email_error").remove();
        document.getElementById(button).type = "submit";
    }
    let input = someEvent.target
    let exists = emails.some((e) => e === someValue);
    let mincharacter = someValue.includes("@")
    if(exists && mincharacter) {
        let errorNode = document.createElement("p");
        errorNode.className = "email_error";
        errorNode.id = "email_error";
        let errorMessage = document.createTextNode("email already exists");
        errorNode.appendChild(errorMessage);
        errorNode.style.color = "red";
        document.querySelector(".errorNode").appendChild(errorNode);
        document.getElementById(button).type = "button";
    }
}

const addDepartment= (someEvent) => {
    let target  = someEvent.target;
    let node2 = document.querySelector(".t1");
    
    if(node2) {
        node2.style.display = "none";
        document.getElementById("department").disabled = true;
    }
    if(target.id === "dept_name") {
        console.log("eee")
        if(target.checked) {
            console.log("add baaaa")
            document.querySelector(".t2").style.display = "flex";
            document.getElementById("dept_name").disabled = false;
        }
    }
}

const showDepartment = (someEvent) => {
    let target = someEvent.target;
    let node2 = document.querySelector(".t2")
    if(node2) {
        node2.style.display = "none";
        document.getElementById("dept_name").disabled = true;
    }
    let isChecked = target.id == "show_department";
    console.log("gg", isChecked)
    if(isChecked) {
        if(target.checked == true) {
            let node1 = document.querySelector(".t1");
            node1.style.display = "flex";
            document.getElementById("department").disabled = false
        }
    }
}

const expandMyMenu = (nodeId) => {
    let node = document.getElementById(nodeId);
    console.log("nn ", nodeId)
    console.log("op", node)
    if(node.className === "HOD_3") {
        node.className = "HOD_3r";
    } else if(node.className === "HOD_3r") {
        node.className = "HOD_3";
    }
}

const showSomething = (nodeName, otherName, targetName, newName = null, event = null) => {
    event?.preventDefault();

    const node = document.getElementById(nodeName) || document.querySelector(`.${nodeName}`);

    if (!node) return;
    if (otherName && targetName) {
        const elements = document.querySelectorAll(`.${otherName}`);
        const targets = document.querySelectorAll(`.${targetName}`)
        for (let i = 0; i < elements.length; i++) {
            elements[i].style.display = "none";
        };
        for (let i = 0; i < targets.length; i++) {
            targets[i].classList.remove(newName);
        }
    }

    if (event && newName) {
        event.target?.parentNode?.classList.add(newName);
    }

    node.style.display = node.style.display === 'none' ? 'flex' : 'none';
};

const show2 = (event, nodeName, otherName, newName) => {
    const node = document.getElementById(nodeName) || document.querySelector(`.${nodeName}`);
    const nodes = document.querySelectorAll(`.${otherName}`)
    nodes.forEach((e) => {
        if(e.classList.contains(newName)) {
            e.classList.remove(newName);
            e.style.display = "none";
        }
        
    });
    node.classList.add(newName);
    node.style.display = "flex";
}

const show3 = (event) => {
    let mytarget = event.target;
    mytarget.style.display = "flex";
}

const show4 =(todo) => {
    let node = document.querySelector(".conf167");
    let header = document.querySelector(".confheader");
    let msg1 = document.querySelector(".confmsg1");
    let msg2 = document.querySelector(".confmsg2");
    if (!node) return;
    if (node.style.display === "none" || node.style.display === "") {
        node.style.display = "flex";
    } else {
        node.style.display = "none";
    }
    if(todo === "del_group") {
        header.textContent = "Delete Group";
        msg1.textContent = "Are you sure you want to delete this group?";
        msg2.textContent = "This action cannot be undone.";
    } else if (todo === "del_staff") {
        header.textContent = "Delete Staff";
        msg1.textContent = "Are you sure you want to delete this staff member?";
        msg2.textContent = "This action cannot be undone.";
    } else if (todo === "del_approver") {
        header.textContent = "Delete Approver";
        msg1.textContent = "Are you sure you want to delete this approver?";
        msg2.textContent = "This action cannot be undone.";
    } else if (todo === "del_holiday") {
        header.textContent = "Delete Holiday";
        msg1.textContent = "Are you sure you want to delete this holiday?";
        msg2.textContent = "This action cannot be undone.";
    } else if (todo === "del_leave_type") {
        header.textContent = "Delete Leave Type";
        msg1.textContent = "Are you sure you want to delete this leave type?";
        msg2.textContent = "This action cannot be undone.";
    }
}



// "input[name='leave_type']"
const setForm = (event, formName, inputType=null) => {
    const originalField = event.target;
    const myForm = document.getElementById(formName);
    const value = originalField.value; // or another unique identifier
    console.log("originalField", originalField)

    const existing = Array.from(myForm.querySelectorAll("input")).find(
        (el) => el.value === value
    );

    if (originalField.checked) {
        if (!existing) {
            const clone = originalField.cloneNode(true);
            clone.type = "hidden";
            myForm.appendChild(clone);
             // Store state
            localStorage.setItem("formName", formName);
            localStorage.setItem("inputType", inputType);
        }
    } else {
        if (existing) {
            myForm.removeChild(existing);
        }
    }
    console.log("mf", myForm)
};

const show1 = (nodeName) => {
    let node = document.getElementById(nodeName) || document.querySelector(`.${nodeName}`);
    if (!node) return;
    if (node.style.display === "none" || node.style.display === "") {
        node.style.display = "flex";
    } else {
        node.style.display = "none";
    }
}

const show5 = (nodeName) => {
    let node = document.getElementById(nodeName) || document.querySelector(`.${nodeName}`);
    if (!node) return;
    if (node.style.visibility === "hidden") {
        node.style.visibility = "visible";
        node.style.opacity = "1";
    } else {
        node.style.display = "hidden";
        node.style.opacity = "0";
    }
}

const rotateMe = (name) => {
    node = document.querySelector(name);
    if(node.style.transform === 'rotate(-90deg)'){
        node.style.transform = 'rotate(180deg)';
    } else {
        node.style.transform = 'rotate(-90deg)'
    }
}

const lvtdell = (event, formName, midName = "lvtmid", inputName = "leave_type") => {
  const myTarget = event.target;
  const myForm = document.querySelector(`.${formName}`);
  if (!myForm) return;

  const targetContainer = myTarget.closest("div");
  const originalInput = targetContainer?.querySelector(`input[name="${inputName}"]`);
  if (!targetContainer || !originalInput) return;

  const hiddenInputs = Array.from(myForm.querySelectorAll("input[type='hidden']"));
  const existingInput = hiddenInputs.find(input => input.value === originalInput.value);

  const btn = targetContainer.querySelector("button");
  const p = targetContainer.querySelector("p");

  const applyStyles = (color, bgColor, btnColor, btnBg, pColor) => {
    Object.assign(targetContainer.style, {
      color,
      backgroundColor: bgColor
    });
    if (btn) {
      btn.style.color = btnColor;
      btn.style.backgroundColor = btnBg;
    }
    if (p) {
      p.style.color = pColor;
    }
  };

  if (existingInput) {
    myForm.removeChild(existingInput);
    applyStyles("black", "#f9f9f9", "black", "#f9f9f9", "black");
  } else {
    const clone = originalInput.cloneNode(true);
    myForm.appendChild(clone);
    applyStyles("gray", "#ddd", "gray", "#ddd", "gray");
  }

  
  // Toggle mid section visibility
  const hasLeaveTypes = myForm.querySelector(`input[name="${inputName}"]`);
  const lvtMid = document.querySelector(`.${midName}`);
  if (lvtMid) {
    lvtMid.style.display = hasLeaveTypes ? "flex" : "none";
  }

};

const mySwitcher2 = (currentNodeName) => {
    let mainNodeName = localStorage.getItem("mainNodeName");
    let mainNode = document.querySelector(mainNodeName);
    let currentNode = document.querySelector(currentNodeName);

    currentNode.style.display = "none";
    mainNode.style.display = "flex";
}

const mySwitcher = (oldSelector, newSelector, mainNodeName=".groups", debug = false) => {
    const oldNode = document.querySelector(oldSelector);
    const newNode = document.querySelector(newSelector);

    if (!oldNode || !newNode) return;

    oldNode.style.display = "none";
    newNode.style.display = "flex";

    if (debug) {
        console.log("Switched from:", oldNode);
        console.log("Switched to:", newNode);
    }
    localStorage.setItem("mainNodeName", mainNodeName);
};


const confirmAction = (event, nodeName, headerName, msg1Name, msg2Name) => {
    document.querySelector(nodeName).style.display = "flex";
    document.querySelector(headerName).textContent = "Delete Leave Types";
    document.querySelector(msg1Name).textContent = "Are you sure you want to delete these leave types?";
    document.querySelector(msg2Name).textContent = "This action cannot be undone.";
}

const lvtdell2 = (formName) => {
  const myForm = document.querySelector(`.${formName}`);
  if (!myForm) return;

  // Remove all hidden inputs
  myForm.querySelectorAll("input[type='hidden']").forEach(input => input.remove());

  // Reset style for leave type containers
  document.querySelectorAll(".lvtlb, .vholitem, .fholitem").forEach(node => {
    Object.assign(node.style, {
      color: "black",
      backgroundColor: "#f9f9f9"
    });

    const btn = node.querySelector("button");
    if (btn) {
      btn.style.color = "black";
      btn.style.backgroundColor = "#f9f9f9";
    }

    const p = node.querySelector("p");
    if (p) {
      p.style.color = "black";
    }
  });

  // Re-check for leave types and toggle mid-section visibility
  const hasLeaveTypes = myForm.querySelector("input[name='leave_type']");
  const lvtMid = document.querySelector(".lvtmid");
  if (lvtMid) {
    lvtMid.style.display = hasLeaveTypes ? "flex" : "none";
  }

  // Re-check for holidays and toggle mid-section visibility
  const hasHolidays = myForm.querySelector("input[name='holiday']");
  const holMid = document.querySelector(".holmid");
  if (holMid) {
    holMid.style.display = hasHolidays ? "flex" : "none";
  }
};


const submitMyForm3 = () => {
    let formName = localStorage.getItem("formName");
    let inputType = localStorage.getItem("inputType");
    const myForm = document.querySelector(`.${formName}`);
    if (!myForm) return;

    // Check if there are any hidden inputs in the form
    const hasHiddenInputs = Array.from(myForm.querySelectorAll(inputType)).length > 0;
    console.log("mm", myForm)
    if(hasHiddenInputs) {
        myForm.submit();
    }
}

const closeadduser = (nodeName, tempName) => {
    const nodes = document.querySelectorAll(`.${nodeName}`);
    nodes.forEach((e) => {
        e.classList.remove(tempName);
        e.style.display = "none";
    })
}

const selectReact = (event, nodeName, selectNode, countNode, totalNode, boxName, selectAllId=null) => {
    const selectWrapper = document.querySelector(selectNode);
    const parent = event.target.parentNode;
    let selectAllNode = null;
    if(selectAllId != null) {
        selectAllNode = document.getElementById(selectAllId)
        selectAllNode.checked = !selectAllNode.checked;
    }
    let myBoxes = [...parent.parentNode.querySelectorAll(boxName)];
    const checkedCount = myBoxes.filter(el => el.checked).length;

    // Highlight selected item
    if (event.target.checked) {
        parent.style.backgroundColor = "#eff3f5";
    } else {
        parent.style.backgroundColor = "inherit";
    }

    // Show .mid only if at least one is checked
    if (checkedCount > 0) {
        selectWrapper.style.display = "flex";
    } else {
        selectWrapper.style.display = "none";
    }
    // Update counts
    document.querySelectorAll(countNode).forEach(e => {
        e.textContent = checkedCount;
    });
    document.querySelectorAll(totalNode).forEach(e => {
        e.textContent = myBoxes.length;
    });
}; 


const submitMyForm4 = (formName, nodeName) => {
    let myForm = document.querySelector(formName);
    if(!myForm){
        return
    }
    localStorage.setItem("prevName", nodeName);
    if (myForm.reportValidity()) {
        myForm.submit();
    }
}

const setMeta = (someValue, formId) => {
    let myForm = document.getElementById(formId);
    let fm = myForm.querySelector('input[name="form_meta"]')
    fm.value = someValue;
}

const selectAllBoxes = (shouldSelect, nodeName, selectNode, countNode, totalNode, motherNode, boxName, selectAllId) => {
    const mother = document.querySelector(motherNode);
    const checkboxes = mother.querySelectorAll(boxName);
    const selectAllNode = document.getElementById(selectAllId) || mother.querySelector(`.${selectAllId}`);

    checkboxes.forEach(box => {
        // Only trigger if the state needs to change
        if (box.checked !== shouldSelect) {
            box.checked = shouldSelect;
        }
    });
    let count = 0;
    let selector  = document.querySelector(selectNode);
    let countSelector = mother.querySelector(countNode);
    let totalSelector = mother.querySelector(totalNode);
    checkboxes.forEach((box)=> {
        // Manually trigger selectReact to handle visual updates and counting
        selectReact({ target: box }, nodeName, selectNode, countNode, totalNode, boxName);
        if(box.checked) {
            count = count + 1;
        }
    })
    if(count > 0 ) {
        selector.style.display = "flex";
    } else {
        selector.style.display = "none";
        selectAllNode.checked = false;
    };
    countSelector.textContent = count;
    totalSelector.textContent = checkboxes.length;
};

const r2sub = (event, formSelector, myURL) => {
    const container = event.target.closest(".workers"); // adjust this class to suit your layout
    if (!container) return;

    container.querySelectorAll(formSelector).forEach(form => {
        form.action = myURL;
        form.submit();
    });
};



const copyNode = (nodeClass, parentClass, buttonId) => {
    const node = document.querySelectorAll(nodeClass)[0];
    const parent = document.querySelector(parentClass);
    const button = document.getElementById(buttonId);

    if (!node || !parent || !button) return; // Ensure elements exist

    const copy = node.cloneNode(true);
    copy.style.display = "flex";
    parent.style.display = "flex";

    // Clear all input, textarea, and select fields inside the cloned node
    copy.querySelectorAll('input, textarea, select').forEach(el => {
        if (el.type === 'checkbox' || el.type === 'radio') {
            el.checked = false;
        } else {
            el.value = '';
        }
    });

    // Check if a similar element already exists
    const existingElement = parent.querySelector("." + button.className);

    // Insert before button if similar element exists, otherwise append
    existingElement ? parent.insertBefore(copy, button) : parent.appendChild(copy);
};

const removeMyElement = (event, parentClass, nodeClass) => {
    let parent = document.querySelector(parentClass);
    let nodes = [...parent.querySelectorAll(nodeClass)];
    let target = event.target;
    let nodeToDelete = null;
    nodes.forEach((e) => {
        if (e.contains(target)) {
            nodeToDelete = e;
        }
    });

    if (nodeToDelete) {
        if(nodes.length >= 2) {
            nodeToDelete.remove();
        } 
    }
};

const closeFirst = (nodeName) => {
    let node = document.getElementById(nodeName) || document.querySelector(`.${nodeName}`);
    node.style.display = "none";
}

const clearMyForm = (formId, inputSelector) => {
    const myForm = document.getElementById(formId);
    if (!myForm) return;

    // Create a static array of matching inputs
    const inputs = Array.from(myForm.querySelectorAll(inputSelector));

    // Remove each input safely
    inputs.forEach(input => input.remove());
};


function switchStaffTab(id, el) {
  const panels = document.querySelectorAll('.staff_panel');
  panels.forEach(p => p.style.display = 'none');

  const tabs = document.querySelectorAll('.staff_nav_item');
  tabs.forEach(t => t.classList.remove('active'));

  document.getElementById(id).style.display = 'block';
  el.classList.add('active');
}

function filterStaffByName(query) {
  const cards = document.querySelectorAll('#staff_all .staff_card');
  const lowerQuery = query.trim().toLowerCase();

  cards.forEach(card => {
    const name = card.querySelector('h4').textContent.toLowerCase();
    card.style.display = name.includes(lowerQuery) ? 'flex' : 'none';
  });
}



const loadSettings = (event = null, itemName = ".general", prevName = ".general") => {
  const item = document.querySelector(itemName);
  const setupPage = document.querySelector(".setup_page");
  const allItems = setupPage ? Array.from(setupPage.children) : [];

  const navItem = document.querySelector(".nav56") || document.querySelector(".nav001");
  const genButton = document.querySelector(".navgen");
  const allNav = document.querySelectorAll(".nav");

  if (!item || !navItem || !genButton) return;

  // Highlight nav
  if (event?.target) {
    allNav.forEach(nav => {
      if(event.target === nav) {
        nav.style.backgroundColor =  "#005a8c";
        nav.style.color = "#fff";
      } else {
        nav.style.backgroundColor = "#fff";
        nav.style.color = "#000";
      }
    });

    if (event.target.classList.contains("navgen")) {
      event.target.style.backgroundColor = "#fff";
    }
  }

  // Hide panels, skip the one with id="nav001"
  allItems.forEach(child => {
    if (
      child.nodeType === 1 &&
      child !== item &&
      child.id !== "nav001"
    ) {
      child.style.display = "none";
    }
  });

  // Adjust nav style
  navItem.className = item.classList.contains("general") ? "nav001" : "nav56";
  genButton.style.display = item.classList.contains("general") ? "none" : "block";

  // Display selected panel
  item.style.display = "flex";

  // Persist selection
  localStorage.setItem("prevName", itemName);
};


const myMenu = (event, nodeName) => {
    let node = document.querySelector(nodeName);
    let allButtons = Array.from(document.querySelectorAll(".app98"));
     if (!node) {
        console.error(`Element with class or ID ${nodeName} not found.`);
        return;
    } else {
        if (node.style.display === "none" || node.style.display === "") {
            node.style.display = "flex";
        } else {
            node.style.display = "none";
        }
    }
    allButtons.forEach((button) => {
        if (button !== event.target) {
            button.style.backgroundColor = "#0077c0"; // Reset background color for other buttons
        } else {
            button.style.backgroundColor = "#005a8c"; // Highlight the clicked button
        }
    })
}

const addApprover = (event, nodeName) => {
    let  = event.target.parentNode.parentNode;
    let node = document.querySelector(nodeName);
    if (!node) {
        console.error(`Element with class or ID ${nodeName} not found.`);
        return;
    }
    if (node.style.display === "none" || node.style.display === "") {
        node.style.display = "flex";
    } else {
        node.style.display = "none";
    }
   
    // Reset the form inside the node
    const form = node.querySelector(".app_form");
    if (form) {
        form.reset();
    }
}

function togglePositionField() {
    const checkbox = document.getElementById("addpositions");
    const positionContainer = document.querySelector(".gp48");
    const positionInput = document.getElementById("position");

    if (checkbox.checked) {
        positionContainer.style.display = "flex"; // Show the field
        positionInput.removeAttribute("disabled"); // Enable input
    } else {
        positionContainer.style.display = "none"; // Hide the field
        positionInput.setAttribute("disabled", "true"); // Disable input
    }
}

const addToMyForm = (nodeName) => {
    let node = document.querySelector(nodeName)?.cloneNode(true);
    if (!node) {
        console.error("Invalid nodeName: No matching element found.");
        return;
    }

    let myForm = document.getElementById("actualForm");
    if (!myForm) {
        console.error("Form not found.");
        return;
    }

    // Remove existing cloned nodes with the same class
    [...myForm.children].forEach(child => {
        if (child.classList.contains(node.className)) {
            myForm.removeChild(child);
        }
    });

    myForm.appendChild(node);
};


const submitTheForm = () => {
    form = document.getElementById("actualForm");
    if(form.childNodes.length > 0) {
        form.submit()
    }
}

const getSomeInfo = () => {
    let os = getOS();
    let screenWidth = window.screen.width;
    let browserInfo = detectBrowser();

    document.getElementById("os_name").value = os.name;
    document.getElementById("os_version").value = os.version;
    document.getElementById("device_type").value = browserInfo.deviceType
    document.getElementById("browser_name").value = browserInfo.name;
    document.getElementById("browser_version").value = browserInfo.version;
}

// const getOS = () => {
//     let userAgent = navigator.userAgent;
//     let platform = navigator.platform;
    
//     if (platform.includes("Win")) return "Windows";
//     if (platform.includes("Mac")) return "MacOS";
//     if (platform.includes("Linux")) return "Linux";
//     if (/Android/.test(userAgent)) return "Android";
//     if (/iPhone|iPad|iPod/.test(userAgent)) return "iOS";
    
//     return "Unknown OS";
// };
const getBrowserInfo = () => {
    let userAgent = navigator.userAgent;
    let browserName = "Unknown Browser";
    let browserVersion = "Unknown Version";

    if (userAgent.includes("Chrome")) {
        browserName = "Chrome";
        browserVersion = userAgent.match(/Chrome\/([\d.]+)/)[1];
    } else if (userAgent.includes("Firefox")) {
        browserName = "Firefox";
        browserVersion = userAgent.match(/Firefox\/([\d.]+)/)[1];
    } else if (userAgent.includes("Safari") && !userAgent.includes("Chrome")) {
        browserName = "Safari";
        browserVersion = userAgent.match(/Version\/([\d.]+)/)[1];
    } else if (userAgent.includes("Edge")) {
        browserName = "Edge";
        browserVersion = userAgent.match(/Edg\/([\d.]+)/)[1];
    }

    return { browserName, browserVersion };
};

/**
 * Detects operating system and version from a user agent string
 * @param {string} [userAgent] -
    Custom user agent string. If not provided, uses navigator.userAgent
 * @returns {Object} Object containing OS name and version
 * @throws {Error} If userAgent parameter is provided but not a string
 */
const getOS = (userAgent) => {
    // Input validation
    if (userAgent !== undefined && typeof userAgent !== 'string') {
        throw new Error('userAgent parameter must be a string');
    }

    // Use provided userAgent or fallback to navigator.userAgent
    const ua = userAgent || (typeof navigator !== 'undefined' ? navigator.userAgent : '');

    const versionFormatt = version => version.replace(/_/g, '.');

    // Enhanced OS detection patterns
    const osMatchers = [
        {
            name: 'Windows',
            regex: /Windows NT ([0-9.]+)/,
            versionMap: {
                '10.0': '10',
                '6.3': '8.1',
                '6.2': '8',
                '6.1': '7',
                '6.0': 'Vista',
                '5.2': 'Server 2003/XP x64',
                '5.1': 'XP',
                '5.0': '2000'
            }
        },
        {
            name: 'MacOS',
            regex: /Mac OS X ([0-9._]+)/,
            versionFormatter: versionFormatt
        },
        {
            name: 'iOS',
            regex: /OS ([\d._]+) like Mac OS X/,
            versionFormatter: versionFormatt
        },
        {
            name: 'iPadOS',
            regex: /iPad.*OS ([\d._]+)/,
            versionFormatter: versionFormatt
        },
        { name: 'Android', regex: /Android ([0-9.]+)/ },
        { name: 'FreeBSD', regex: /FreeBSD/ },
        { name: 'OpenBSD', regex: /OpenBSD/ },
        { name: 'NetBSD', regex: /NetBSD/ },
        { name: 'Solaris', regex: /SunOS/ },
        { name: 'BlackBerry', regex: /BB10|BlackBerry/ },
        { name: 'KaiOS', regex: /KaiOS ([0-9.]+)/ },
        { name: 'Windows Phone', regex: /Windows Phone ([0-9.]+)/ },
        {
            name: 'Linux',
            regex: /Linux/,
            distributions: [
                { name: 'Ubuntu', regex: /Ubuntu/ },
                { name: 'Fedora', regex: /Fedora/ },
                { name: 'Red Hat', regex: /Red Hat/ },
                { name: 'Debian', regex: /Debian/ }
            ]
        },
        {
            name: 'Chrome OS',
            regex: /CrOS/
        }
    ];

    for (const os of osMatchers) {
        const match = ua.match(os.regex);
        if (match) {
            let version = match[1] || 'Unknown Version';

            // Handle Windows version mapping
            if (os.name === 'Windows' && os.versionMap?.[version]) {
                version = os.versionMap[version];
            }

            // Handle version formatting (e.g., for MacOS and iOS)
            if (os.versionFormatter) {
                version = os.versionFormatter(version);
            }

            // Handle Linux distributions
            if (os.name === 'Linux' && os.distributions) {
                for (const dist of os.distributions) {
                    if (ua.match(dist.regex)) {
                        return {
                            name: `${dist.name} Linux`,
                            version: 'Unknown Version',
                            baseOS: 'Linux'
                        };
                    }
                }
            }

            return { name: os.name, version };
        }
    }

    return { name: 'Unknown OS', version: 'Unknown Version' };
};

// Browser detection function
const detectBrowser = () => {
    const userAgent = navigator.userAgent;

    const browsers = [
        { name: 'Brave', test: () => navigator.brave && navigator.brave.isBrave !== undefined, versionRegex: /Chrome\/([0-9.]+)/ },
        { name: 'Yandex Browser', test: /YaBrowser/, versionRegex: /YaBrowser\/([0-9.]+)/ },
        { name: 'Microsoft Edge', test: /Edg/, versionRegex: /Edg\/([0-9.]+)/ },
        { name: 'Mozilla Firefox', test: /Firefox/, versionRegex: /Firefox\/([0-9.]+)/ },
        { name: 'Opera', test: /Opera|OPR/, versionRegex: /(?:Opera|OPR)\/([0-9.]+)/ },
        { name: 'Vivaldi', test: /Vivaldi/, versionRegex: /Vivaldi\/([0-9.]+)/ },
        { name: 'DuckDuckGo Browser', test: /DuckDuckGo/, versionRegex: /DuckDuckGo\/([0-9.]+)/ },
        { name: 'Tor Browser', test: () => userAgent.includes('TorBrowser'), versionRegex: /TorBrowser\/([0-9.]+)/ },
        { name: 'UC Browser', test: /UCBrowser/, versionRegex: /UCBrowser\/([0-9.]+)/ },
        { name: 'Samsung Internet', test: /SamsungBrowser/, versionRegex: /SamsungBrowser\/([0-9.]+)/ },
        { name: 'QQ Browser', test: /QQBrowser/, versionRegex: /QQBrowser\/([0-9.]+)/ },
        { name: 'Baidu Browser', test: /BaiduBrowser/, versionRegex: /BaiduBrowser\/([0-9.]+)/ },
        { name: 'Amazon Silk', test: /Silk/, versionRegex: /Silk\/([0-9.]+)/ },
        { name: 'Vivo Browser', test: /VivoBrowser/, versionRegex: /VivoBrowser\/([0-9.]+)/ },
        { name: 'Miui Browser', test: /MiuiBrowser/, versionRegex: /MiuiBrowser\/([0-9.]+)/ },

        { name: 'Google Chrome', test: /Chrome(?!.*(?:Edg|Brave|YaBrowser))/, versionRegex: /Chrome\/([0-9.]+)/ },
        { name: 'Safari', test: /Safari(?!.*Chrome)/, versionRegex: /Version\/([0-9.]+)/ },
    ];

    // Helper to extract version from userAgent using regex
    const getVersion = (regex) => {
        const match = userAgent.match(regex);
        return match ? match[1] : 'Unknown Version';
    };

    // Function to detect the operating system
    const detectOS = () => {
        const osMatchers = [
            { name: 'Windows', regex: /Windows NT ([0-9.]+)/ },
            { name: 'MacOS', regex: /Mac OS X ([0-9._]+)/ },
            { name: 'Linux', regex: /Linux/ },
            { name: 'iOS', regex: /iPhone|iPad/ },
            { name: 'Android', regex: /Android ([0-9.]+)/ },
            { name: 'Android', regex: /Android ([0-9.]+)/ },
        ];

        for (const os of osMatchers) {
            const match = navigator.userAgent.match(os.regex);
            if (match) {
                return { name: os.name, version: match[1] || 'Unknown Version' };
            }
        }
        return { name: 'Unknown OS', version: 'Unknown Version' };
    };

    // Function to detect the device type
    const detectDeviceType = () => {
        const userAgent = navigator.userAgent.toLowerCase();
        if (/mobi|android|iphone|ipad|windows phone/i.test(userAgent)) return 'mobile';
        if (/tablet|ipad/i.test(userAgent)) return 'tablet';
        return 'desktop';
    };

    // Detect other browsers
    for (const browser of browsers) {
        const isMatch =
            typeof browser.test === 'function' ?
            browser.test() :
            browser.test.test(userAgent);

        if (isMatch) {
            return {
                name: browser.name,
                version: getVersion(browser.versionRegex),
                os: detectOS(),
                deviceType: detectDeviceType(),
            };
        }
    }

    // Default fallback
    return {
        name: 'Unknown Browser',
        version: 'Unknown Version',
        os: detectOS(),
        deviceType: detectDeviceType(),
    };
};

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

