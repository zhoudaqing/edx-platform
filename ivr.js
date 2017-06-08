// Retrieve the utils library
var utils = window.optimizely.get('utils');

// Wait for the upgrade link element to appear in the DOM, then change the color
utils.waitForElement('.upgrade-link').then(function(upgradeLink) {
    var upgradeUser = document.getElementById('upgrade_user');
    upgradeLink.href = upgradeUser.dataset.link;
    upgradeLink.innerHTML += " (" + upgradeUser.dataset.price + ")";
});

$(function () {
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
    // TODO Fire Optimizely event
    toggleHeroExpansion();
  });
});
