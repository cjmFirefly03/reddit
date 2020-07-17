// ==UserScript==
// @name        RedditRaffle
// @namespace   redditraffle
// @description Choses a list of winners by certain criteria
// @include     https://www.reddit.com/r/*/comments/*
// @version     1.6
// @grant       GM_xmlhttpRequest
// @grant       GM_addStyle
// ==/UserScript==

var link,
    url,
    winner_count,
    author_exclude,
    keyword_included,
    keyword_excluded,
    karma_link,
    karma_comment,
    age = 0,
    total_comments,
    comments = [],
    more = [],
    more_lock = false,
    parse_lock = false,
    names = [],
    chosen = [],
    userinfo,
    query_interval,
    connection_count = 0;

function render_results() {
    progress.innerHTML = "<button class=\"results\">Show Results</button>";
    var raffleResults = document.querySelector(".raffle-results")
    raffleResults.innerHTML = "Rendering:";
    var html = [];
    html.push("<!doctype html><meta charset=\"utf-8\" /><title>Raffle results</title>" +
              "<style>table{overflow:hidden;border:1px solid #d3d3d3;background:#fefefe;" +
              "width:80%;margin:auto;-moz-border-radius:5px;-webkit-border-radius:5px;" +
              "border-radius:5px;-moz-box-shadow: 0 0 4px rgba(0, 0, 0, 0.2);" +
              "-webkit-box-shadow: 0 0 4px rgba(0, 0, 0, 0.2);}th,td{text-align:center;}" +
              "th{padding:14px 22px;text-shadow: 1px 1px 1px #fff;background:#e8eaeb;}" +
              "td{border-top:1px solid #e0e0e0;border-right:1px solid #e0e0e0;}" +
              "tr:nth-child(odd) td{background:#f6f6f6;}td:last-child{border-right:none;" +
              "text-align:left;padding:8px 18px;}</style><table><tr><th>No.</th><th>User</th>" +
              "<th>Comment</th></tr>");
    var winner_length = Math.min(winner_count, chosen.length);
    for(var i = 0; i < winner_length; i++) {
        html.push("<tr><td>" + (i + 1) + ".</td><td><a href=\"http://www.reddit.com/user/" +
                  chosen[i].author + "\">" + chosen[i].author + "</a></td><td>");
        html.push(chosen[i].body_html.replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&'));
        html.push("<br/><a href=\"" + url + '/' + chosen[i].id + "\">Show</a></td><tr>");
    }
    html.push("</table>");
    raffleResults.innerHTML = html.join('');
}

function query_users() {
    if(more_lock || parse_lock) return;
    var commentsLeft = [].concat(comments);
    query_interval = window.setInterval(function() {
        //console.log(commentsLeft);
        if(chosen.length >= winner_count || !commentsLeft.length) {
            window.clearInterval(query_interval);
            render_results();
            return;
        }
        if(connection_count > 10) return;
        var comment = commentsLeft.splice(Math.floor(Math.random() * commentsLeft.length), 1)[0];
        if(comment === undefined ||
           comment.body.toLowerCase().indexOf(keyword_included) < 0 ||
           (keyword_excluded && !(comment.body.toLowerCase().indexOf(keyword_excluded) < 0)) ||
           (author_exclude && comment.author === author_exclude) ||
           !(names.indexOf(comment.author) < 0)) {
            return;
        }
        if(age || karma_link || karma_comment) {
            GM_xmlhttpRequest({
                method: 'GET',
                url: 'http://www.reddit.com/user/' + comment.author + '/about.json',
                context: comment,
                onload: function(response) {
                    connection_count--;
                    userinfo = JSON.parse(response.responseText).data;
                    if((!age || userinfo.created_utc <= age) &&
                       userinfo.link_karma >= karma_link &&
                       userinfo.comment_karma >= karma_comment &&
                       chosen.length < winner_count &&
                       names.indexOf(comment.author) < 0) {
                        names.push(userinfo.name);
                        chosen.push(response.context);
                        progress.innerHTML = "Querying Users: " + chosen.length + "/" + winner_count;
                    }
                },
                onerror: function(error) {
                    connection_count--;
                    console.log(error);
                },
            });
            connection_count++;
        } else {
            names.push(comment.author);
            chosen.push(comment);
            progress.innerHTML = "Querying Users: " + chosen.length + "/" + winner_count;
        }
    }, 100);
}

function add_comment(comment) {
    comments.push(comment);
    if(comment.replies && comment.replies.kind === "Listing") {
        parse_listing(comment.replies.data.children);
    }
}

function add_more(children) {
    more.push.apply(more, children);
    if(!more_lock) parse_more();
}

function parse_more() {
    if(!more.length) {
        more_lock = false;
        query_users();
        return;
    }
    more_lock = true;
    var children = more.splice(0, 20);
    GM_xmlhttpRequest({
        method: 'POST',
        url: 'http://www.reddit.com/api/morechildren.json',
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data: 'link_id=' + link + '&api_type=json&children=' + children.join(),
        onload: function(response) {
            parse_listing(JSON.parse(response.responseText).json.data.things);
            progress.innerHTML = "Parsing Comments: " + comments.length + "/" + total_comments;
            parse_more();
        },
        enerror: function(error) {
            more.push.apply(more, children);
            console.log("Error:", error);
            parse_more();
        }
    });
}

function parse_listing(listing) {
    var listingLength = listing.length;
    for(var child = 0; child < listingLength; child++) {
        if (listing[child].kind === 't1') {
            add_comment(listing[child].data);
        }
        else if (listing[child].kind === 't3') {
            link = listing[child].data.name;
            author_exclude = form.elements.author_exclude.checked ? listing[child].data.author : "";
            total_comments = listing[child].data.num_comments;
            progress.innerHTML = "Parsing Comments: 0/" + total_comments;
        }
        else if (listing[child].kind === 'more') {
            add_more(listing[child].data.children);
        }
    }
}

function do_raffle() {
    if (chosen.length) {
        reset_raffle();
    }
    progress.innerHTML = "Parsing Comments:";
    winner_count = parseInt(form.elements.winner_count.value) || 20;
    keyword_included = form.elements.keyword_included.value.toLowerCase();
    keyword_excluded = form.elements.keyword_excluded.value.toLowerCase();
    karma_link = parseInt(form.elements.karma_link.value) || 0;
    karma_comment = parseInt(form.elements.karma_comment.value) || 0;
    if(form.elements.age_days.value ||
       form.elements.age_month.value ||
       form.elements.age_years.value) {
        var date = new Date();
        date.setDate(date.getDate() - (parseInt(form.elements.age_days.value) || 0));
        date.setMonth(date.getMonth() - (parseInt(form.elements.age_month.value) || 0));
        date.setFullYear(date.getFullYear() - (parseInt(form.elements.age_years.value) || 0));
        age = date.getTime()/1000;
    }
    url = window.location.href;
    url = url.replace(/\/+$/, "");
    if(url.indexOf("?") > -1) {
        url = url.substring(0, url.indexOf("?"));
    }
    if (comments.length > 0) {
        query_users();
    }
    else {
        parse_lock = true;
        //console.log(url);
        GM_xmlhttpRequest({
            method: 'GET',
            url: url + '.json',
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data: 'limit=500',
            onload: function(response) {
                var things = JSON.parse(response.responseText),
                    thingsLength = things.length
                for(var thing = 0; thing < thingsLength; thing++) {
                    if (things[thing].kind === 'Listing') {
                        parse_listing(things[thing].data.children);
                    }
                }
                parse_lock = false;
                query_users();
            },
        });
    }
}

function reset_raffle() {
    chosen = [];
    names = [];
}

function toggle_flyout() {
    var raffleElement = document.querySelector('.reddit-raffle');
    raffleElement.classList.toggle("reddit-raffle--hidden");
}

function show_results() {
    var raffleElement = document.querySelector('.reddit-raffle');
    raffleElement.classList.add('reddit-raffle--show-results');
}

var css = document.createElement("style");
css.type = "text/css";
css.innerHTML = "\
.reddit-raffle {\
    position: fixed;\
    left: calc(100% - 324px);\
    top: 0;\
    bottom: 0;\
    z-index: 1000000000000000;\
    display: flex;\
    transition: left 1s;\
    width: 100%;\
}\
.reddit-raffle--show-results {\
    left: 0;\
}\
.reddit-raffle--hidden {\
    left: calc(100% - 32px);\
}\
.raffle-content {\
    padding: 8px;\
    background-color: white;\
    border-radius: 4px 0 0 4px;\
    align-self: center;\
}\
.raffle-results {\
    background-color: white;\
    width: 100%;\
    margin: 0 auto;\
    overflow: auto;\
    padding: 32px;\
}\
.raffle-form input[type=text]{\
	width:265px;\
	border:1px solid #000000;\
	-moz-border-radius:2px;\
	-webkit-border-radius:2px;\
	-o-border-radius:2px;\
	-ms-border-radius:2px;\
	-khtml-border-radius:2px;\
	border-radius:2px;\
	font-size:14px;\
	font-style:italic;\
	padding:4px;\
    margin-bottom: 8px;\
}\
#toggle-flyout {\
    writing-mode: vertical-rl;\
    text-orientation: upright;\
    padding: 8px;\
    cursor: pointer;\
    background-color: white;\
    align-self: center;\
    border-radius: 4px 0 0 4px;\
}\
";

var spacer = document.createElement("div");
spacer.appendChild(css);
spacer.classList.add("reddit-raffle","reddit-raffle--hidden");
spacer.innerHTML = "<div id=\"toggle-flyout\">\
    Reddit Raffle\
    </div>\
    <div class=\"raffle-content \">\
	    <div class=\"title\"><h1>Raffle</h1></div>\
	    <form class=\"raffle-form\">\
		    <ul class=\"content\">\
			    <li><input type=\"text\" placeholder=\"Number of Winners\" name=\"winner_count\" /></li>\
			    <li><input type=\"text\" placeholder=\"Comments containing\" name=\"keyword_included\" /></li>\
			    <li><input type=\"text\" placeholder=\"Comments not containing\" name=\"keyword_excluded\" /></li>\
			    <li><input type=\"text\" placeholder=\"Required Link Karma\" name=\"karma_link\" /></li>\
			    <li><input type=\"text\" placeholder=\"Required Comment Karma\" name=\"karma_comment\" /></li>\
			    <li><input type=\"text\" placeholder=\"Age in Days\" name=\"age_days\" /></li>\
			    <li><input type=\"text\" placeholder=\"Age in Months\" name=\"age_month\" /></li>\
			    <li><input type=\"text\" placeholder=\"Age in Years\" name=\"age_years\" /></li>\
			    <li>\
                    <button class=\"save\" type=\"button\">Raffle</button>\
                    <input type=\"checkbox\" name=\"author_exclude\" id=\"author_exclude\" checked=\"checked\"/>\
                    <label for=\"author_exclude\">Exclude Author</label>\
                </li>\
		    </ul>\
	    </form>\
        <div class=\"raffle-progress\"></div>\
    </div>\
<div class=\"raffle-results\">\
</div>\
";
var form = spacer.querySelector("form.raffle-form"),
    progress = spacer.querySelector(".raffle-progress"),
    body = document.querySelector("body");

body.appendChild(spacer);
body.appendChild(css);
document.querySelector("#toggle-flyout").addEventListener("click", toggle_flyout);
form.querySelector("button").addEventListener("click", do_raffle, true);
progress.addEventListener("click", clickListner);

function clickListner(event){
    var element = event.target;
    if(element.classList.contains('results')) {
        show_results();
    }
}




