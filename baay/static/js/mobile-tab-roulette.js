/**
 * Mixin Alpine pour navigation d'onglets en « roulette » sur mobile.
 * Usage : Object.assign({ activeTab, setTab... }, tabRouletteMixin({ order, select }))
 */
(function () {
    'use strict';

    var MOBILE_MQ = window.matchMedia('(max-width: 767.98px)');

    function tabRouletteMixin(options) {
        var order = options.order || [];
        var select = options.select;

        return {
            tabRouletteOrder: order,

            rouletteSelect: function (tab) {
                if (select) {
                    select.call(this, tab);
                } else {
                    this.activeTab = tab;
                }
                var self = this;
                this.$nextTick(function () {
                    self.rouletteScrollActive();
                });
            },

            roulettePrev: function () {
                var i = order.indexOf(this.activeTab);
                if (i < 0) {
                    return;
                }
                var prev = order[(i - 1 + order.length) % order.length];
                this.rouletteSelect(prev);
            },

            rouletteNext: function () {
                var i = order.indexOf(this.activeTab);
                if (i < 0) {
                    return;
                }
                var next = order[(i + 1) % order.length];
                this.rouletteSelect(next);
            },

            rouletteScrollActive: function () {
                if (!MOBILE_MQ.matches) {
                    return;
                }
                var nav = this.$refs.tabRouletteNav;
                if (!nav) {
                    return;
                }
                var btn = nav.querySelector('[data-tab-id="' + this.activeTab + '"]');
                if (btn) {
                    btn.scrollIntoView({ inline: 'center', behavior: 'smooth', block: 'nearest' });
                }
            },

            initTabRoulette: function () {
                var self = this;
                this.$watch('activeTab', function () {
                    self.$nextTick(function () {
                        self.rouletteScrollActive();
                    });
                });
                this.$nextTick(function () {
                    self.rouletteScrollActive();
                });
            },

            initTabRouletteScrollSync: function () {
                var self = this;
                var nav = this.$refs.tabRouletteNav;
                if (!nav) {
                    return;
                }
                var scrollTimer;
                var syncReady = false;
                setTimeout(function () {
                    syncReady = true;
                }, 500);
                nav.addEventListener(
                    'scroll',
                    function () {
                        if (!syncReady || !MOBILE_MQ.matches) {
                            return;
                        }
                        clearTimeout(scrollTimer);
                        scrollTimer = setTimeout(function () {
                            var center = nav.scrollLeft + nav.clientWidth / 2;
                            var buttons = nav.querySelectorAll('[data-tab-id]');
                            var best = null;
                            var bestDist = Infinity;
                            buttons.forEach(function (btn) {
                                var mid = btn.offsetLeft + btn.offsetWidth / 2;
                                var dist = Math.abs(mid - center);
                                if (dist < bestDist) {
                                    bestDist = dist;
                                    best = btn;
                                }
                            });
                            if (!best) {
                                return;
                            }
                            var tab = best.getAttribute('data-tab-id');
                            if (tab && tab !== self.activeTab) {
                                self.rouletteSelect(tab);
                            }
                        }, 140);
                    },
                    { passive: true }
                );
            },
        };
    }

    window.tabRouletteMixin = tabRouletteMixin;
})();
