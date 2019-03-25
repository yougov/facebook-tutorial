function screen_log(message) {
  document.querySelector('#content').innerHTML += message + '<br />'
}


function handle_posts(posts) {
  screen_log("Found " + posts.length + " posts")
}

window.fbAsyncInit = function() {
  FB.init(facebook_options);
  FB.login(function(response) {
    if (response.authResponse) {
      screen_log('Welcome!  Fetching your information.... ');
      FB.api('/me', function(response) {
        screen_log('Good to see you, ' + response.name + '.');
      });
      fetch('/posts?access_token=' + response.authResponse.accessToken)
        .then(response => response.json())
        .then(handle_posts)
    } else {
      console.log('User cancelled login or did not fully authorize.');
    }
  }, {
    scope: facebook_scope
  }
  );
};
