// Retrieve the utils library
var utils = window.optimizely.get('utils');

// Wait for the upgrade link element to appear in the DOM, then change the color
utils.waitForElement('.upgrade-link').then(function(upgradeLink) {
    var upgradeUser = document.getElementById('upgrade_user');
    upgradeLink.href = upgradeUser.dataset.link;
    upgradeLink.innerHTML += " (" + upgradeUser.dataset.price + ")";
});
