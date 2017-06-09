// Retrieve the utils library
var utils = window.optimizely.get('utils');

selector = '#course-info-progress .chapters,.info-wrapper,main.course-outline,.view-discussion-home';

// Wait for the upgrade link element to appear in the DOM, then change the color
utils.waitForElement(selector).then(function(container) {
  var upgradeUser = document.getElementById('upgrade_user');
  content = ' \
      <div class="verification-hero-wrapper" style="display:none;"> \
      <div class="verification-hero-toggle-wrapper"> \
        <a class="verification-hero-toggle" href="#" aria-expanded="true">Show less</a> \
      </div> \
      <div class="verification-hero"> \
        <div class="copy-and-button"> \
          <div class="copy"> \
            <div class="title">Pursue a verified certificate</div> \
            <ul> \
              <li>Official proof of completion</li> \
              <li>Easily shareable certificate</li> \
              <li>Proven motivator to complete the course</li> \
              <li>Certificate purchases help edX continue to offer free courses \
              </li> \
            </ul> \
          </div> \
          <div class="upgrade-button"> \
            <a class="btn btn-brand upgrade-link" href="{addToCartUrl}"> \
              Upgrade Now ({price}) \
            </a> \
          </div> \
        </div> \
        <div class="certificate-image"> \
          <img src="https://www.edx.org/sites/default/files/professional-certficate-example-universityx-500x342.png?0002" alt="Certificate example"/> \
        </div> \
      </div> \
      <div class="verification-sidekick" style="display:none"> \
        <div class="certificate-image"> \
          <img src="https://courses.edx.org/static/images/edx-verified-mini-cert.png" alt="Certificate example"/> \
        </div> \
        <div class="title">Pursue a verified certificate</div> \
        <div class="upgrade-button"> \
          <a class="btn btn-brand upgrade-link" href="{addToCartUrl}"> \
            Upgrade Now ({price}) \
          </a> \
        </div> \
        <div style="clear:both"></div> \
      </div> \
    </div>'.replace(/{addToCartUrl}/g, upgradeUser.dataset.link).replace(/{price}/g, upgradeUser.dataset.price);

  $(container).prepend(content);

  var STATUS_KEY = 'ret.verificationHeroExpanded',
    $verificationHeroOuter = $('.verification-hero-wrapper'),
    $verificationHero = $verificationHeroOuter.find('.verification-hero'),
    $verificationSidekick = $verificationHeroOuter.find('.verification-sidekick'),
    $toggleWrapper = $verificationHeroOuter.find('.verification-hero-toggle-wrapper'),
    $toggle = $toggleWrapper.find('.verification-hero-toggle');

  // Hide the hero if the user previously hid it
  if (localStorage.getItem(STATUS_KEY) === 'false') {
    $verificationHero.hide();
    $verificationSidekick.show();
    $toggle.attr('aria-expanded', false);
    $toggleWrapper.remove();
  }

  $verificationHeroOuter.fadeIn('slow');

  function toggleHeroExpansion() {
    var expanded = $toggle.attr('aria-expanded') === 'true';

    if (expanded) {
      // Collapse the hero, and bring in the sidekick
      $verificationHero.slideToggle('slow', function () {
        $toggle.attr('aria-expanded', !expanded);
        $verificationSidekick.toggle(100);
        $toggleWrapper.remove();
      });
    }
    else {
      // Collapse the sidekick, and call in the big guy!
      $verificationSidekick.toggle(100, function () {
        $verificationHero.slideToggle('slow', function () {
          $toggle.attr('aria-expanded', !expanded);
        });
      });
    }

    localStorage.setItem(STATUS_KEY, !expanded);
  }

  $toggle.click(function () {
    toggleHeroExpansion();
  });
});