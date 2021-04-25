let loggedIn    //are these usefuL?
let username
let gameCreateButtons = []
let gameColors = []


getGames()
authorize()


function getGames() {
    const allGamesGET = $.ajax({
        url: "/games",
        type: "GET",
        success: function () {
            let games = allGamesGET.responseJSON
            let games_list = document.getElementById("list-games");
            for (var i = 0; i < games.length; i++) {
                const x = games[i][0]
                if (games[i][2] == true) {
                    gameCreateButtons.push(x)
                    gameColors.push(games[i][1])
                }
                var btnHTML = '<div class="item"><button id="btn-' + x + '" class="ui ' + games[i][1]
                    + ' disabled button" style="opacity: 1;" onclick="create(\'' + x + '\')">' + x
                    + '</button></div>'
                games_list.innerHTML += btnHTML
            }
        },
        error: function () {
            console.log("cant even get games.")
            logout()
        }

    });
}

function logout() {
    window.localStorage.removeItem("RPAtoken")
    document.getElementById("div-logout-btn").style.display = "none"
    document.getElementById("div-login-bar").style.display = "block"
    document.getElementById("list-messages").innerHTML = ""
    document.getElementById("list-current-games").innerHTML = ""
    document.getElementById("btn-newmessage").classList.add("disabled")
    document.getElementById("name").value = ""
    document.getElementById("password").value = ""
    // TODO disable create buttons
    console.log(gameCreateButtons)
    gameCreateButtons.forEach(disable_create_button);

    username = ""
    loggedIn = false
}


function authorize() {
    const token = window.localStorage.getItem("RPAtoken")
    const user = $.ajax({
        url: "/me",
        type: "GET",
        beforeSend: function (xhr) {
            xhr.setRequestHeader('Authorization', "Bearer " + token);
        },
        success: function () {
            console.log("authorized, hiding loginbar, showing logout button")
            loggedIn = true
            document.getElementById("div-login-bar").style.display = "none"
            username = user.responseJSON["username"]
            document.getElementById('label-logout').innerHTML = "<i class=\"icon user\"></i>" + username
            document.getElementById("div-logout-btn").style.display = ""
            document.getElementById("btn-newmessage").classList.remove("disabled")

            // TODO enable create button
            getMyRecentMessages()
            getMyCurrentGames()
            gameCreateButtons.forEach(enable_create_button);
        },
        error: function () {
            console.log("no authorization")
            logout()
        }
    });
}


function getMyCurrentGames() {
    const token = window.localStorage.getItem("RPAtoken")
    const myGamesGET = $.ajax({
        url: "/myCurrentGames",
        type: "GET",
        beforeSend: function (xhr) {
            xhr.setRequestHeader('Authorization', "Bearer " + token);
        },
        success: function () { //save this someplace
            let games = myGamesGET.responseJSON
            console.log(games)
            let current_games_list = document.getElementById("list-current-games")
            for (let i = 0; i < games.length; i++) {
                btnHTML = '<div class="item"><div class="ui left labeled button"><a class="ui blue label">'
                    + games[i]["my_score"] + ' - ' + games[i]["opponent_score"] + '</a><div class="ui icon button" onclick="showGame(' + games[i]["id"] + ')">vs. '
                    + games[i]["opponent"]
                    + '</div></div></div>'

                current_games_list.innerHTML += btnHTML
            }
        },
        error: function () {

        }
    })

}

function getMyRecentMessages() {
    const token = window.localStorage.getItem("RPAtoken")
    const mymessagesGET = $.ajax({
        url: "/myrecentmessages",
        type: "GET",
        beforeSend: function (xhr) {
            xhr.setRequestHeader('Authorization', "Bearer " + token);
        },
        success: function () {
            console.log("fetching recent messages")
            let msg_list = document.getElementById("list-messages")
            const messages = mymessagesGET.responseJSON
            let max = messages.length - 5;
            if (max < 0)
                max = 0
            for (let i = messages.length - 1; i >= max; i--) {


                current = messages[i]
                prettyDate = dateConvert(current["date"])
                //TODO reply knopf mal mindestens

                if (current["content"].length > 140) {
                    current["content"] = current["content"].substr(0, 140)
                    current["content"] += " ..."        // TODO probably make the dots into a link that shows the full message or something like that
                }

                var msgHTML = '<div class="comment"><a class="avatar">\n' +
                    '                        <img src="avatar/' + current["sender_avatar"] + '">\n' +
                    '                    </a><div class="content">\n' +
                    '                        <a class="author">' + current["sender"] + '</a><div class="metadata">\n' +
                    '                            <span class="date">' + prettyDate + '</span>\n' +
                    '                        </div><div class="text">' + current["content"] + '</div><div class="actions" onclick="reply(\'' + current["sender"] + '\')">\n' +
                    '                            <a class="reply">Reply</a>\n' +
                    '                        </div></div>'
                msg_list.innerHTML += msgHTML


            }
        }

    });
}

function disable_create_button(game) {
    console.log("disabling " + game)
    document.getElementById("btn-" + game).classList.add("disabled")
}

function enable_create_button(game) {
    console.log("enable " + game)
    document.getElementById("btn-" + game).classList.remove("disabled")
}


function showGame(id) {
    console.log("showgame " + id)
}

function reply(name) {
    document.getElementById("field-recipient").classList.remove('error')
    document.getElementById("input-recipient").value = name
    document.getElementById("input-message").value = ""
    $('#modal-newmessage').modal('show')
    $("#input-message").focus(); // TODO after this is executed, focus jumps back to the recipient field. why?
}

function dateConvert(datetime) {
    //TODO wie machen echte leute das?
    //console.log(datetime)
    let prettyDate = ""
    for (let i = 11; i < 16; i++)
        prettyDate += datetime[i]
    prettyDate += " on "
    prettyDate += datetime[5]
    prettyDate += datetime[6]
    prettyDate += "/"
    prettyDate += datetime[8]
    prettyDate += datetime[9]
    prettyDate += "/"
    prettyDate += datetime[2]
    prettyDate += datetime[3]
    return prettyDate
}

//TODO
function create(game) {
    console.log("create ", game)
}

function send() {
    const recipient = document.getElementById("input-recipient").value
    const content = document.getElementById("input-message").value
    const token = window.localStorage.getItem("RPAtoken")
    const send = $.ajax({
        url: "/send/",
        type: "POST",
        beforeSend: function (xhr) {
            xhr.setRequestHeader('Authorization', "Bearer " + token);
        },
        contentType: 'application/json',
        data: JSON.stringify({"recipient": recipient, "content": content}),
        dataType: 'json',
        success: function () {
            console.log("sent successfully")
            document.getElementById("field-recipient").classList.remove('error')
            document.getElementById("input-recipient").value = ""
            document.getElementById("input-message").value = ""
            $('#modal-newmessage').modal('hide').modal('hide dimmer');
        },
        error: function () {
            // TODO hier koennte irgendwas anderes schiefgehen?
            //  generelle fehlermeldung ala oops smth went wrong
            console.log(send.responseJSON)
            document.getElementById("field-recipient").classList.add('error')
            //document.getElementById("input-recipient").setAttribute("data-content", "popup")
        }
    });
}
