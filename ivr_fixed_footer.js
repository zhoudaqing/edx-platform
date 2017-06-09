// Retrieve the utils library
var utils = window.optimizely.get('utils');

// Wait for the upgrade link element to appear in the DOM, then change the color
utils.waitForElement("footer").then(function(container) {
  var upgradeUser = document.getElementById('upgrade_user');
  if (upgradeUser === null) {
    return;
  }
  $(container).before(' \
    <div class="verification-sock" role="region" aria-label="Upgrade to Verified"> \
      <div class="verification-sock-inner"> \
        <div class="copy"> \
            <h2 class="title">Pursue a Verified Certificate</h2> \
            <div class="upgrade-button"> \
              <a class="btn btn-brand upgrade-link" href="{addToCartUrl}"> \
                Upgrade Now ({price}) \
              </a> \
            </div> \
          </div> \
          <div class="certificate-image"> \
            <img src="https://courses.edx.org/static/images/edx-verified-mini-cert.png" alt="Certificate example"/> \
          </div> \
        </div> \
    </div>'.replace(/{addToCartUrl}/g, upgradeUser.dataset.link).replace(/{price}/g, upgradeUser.dataset.price)
  );

  $('.upgrade-link').click(function(event) {
    window.optimizely.push(['trackEvent', 'upgrade_banner']);
  });
});
