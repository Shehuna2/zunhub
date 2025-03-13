(function ($) {
  /* "use strict" */

  var tfAreaChart = (function () {
    let draw = Chart.controllers.line.__super__.draw; //draw shadow
    var screenWidth = $(window).width();

    var areaChart1 = function () {
      var options1 = {
          series: [
            {
              data: [
                1.128307699, 1.428307699, 1.228307699, 1.328307699, 1.2124344,
                1.4283077, 1.32830745, 1.528307699, 1.428312, 1.4383234,
                1.32830745, 1.628307699, 1.128307699,
              ],
            },
          ],
          colors: ["#25C866"],
          chart: {
            type: "area",
            Width: 390,
            height: 205,
            sparkline: { enabled: !0 },
          },
          plotOptions: { bar: { columnWidth: "50%" } },
          xaxis: { crosshairs: { width: 1 } },

          stroke: {
            show: true,
            curve: "smooth",
            lineCap: "butt",
            colors: undefined,
            width: 1,
            dashArray: 0,
          },

          tooltip: {
            // enabled: false,
            fixed: { enabled: !1 },
            x: { show: !1 },
            y: {
              title: {
                formatter: function (e) {
                  return "";
                },
              },
            },
            marker: { show: !1 },
          },

          states: {
            hover: {
              filter: {
                type: "none",
                value: 0,
              },
            },
          },
        },
        chart1 = new ApexCharts(
          document.querySelector(".area-chart-1"),
          options1
        );
      chart1.render();
    };
    var areaChart2 = function () {
      var options2 = {
          series: [
            {
              data: [
                1.128307699, 1.428307699, 1.228307699, 1.328307699, 1.2124344,
                1.4283077, 1.32830745, 1.528307699, 1.428312, 1.4383234,
                1.32830745, 1.628307699, 1.128307699,
              ],
            },
          ],
          colors: ["#25C866"],
          chart: {
            type: "area",
            Width: 390,
            height: 205,
            sparkline: { enabled: !0 },
          },
          plotOptions: { bar: { columnWidth: "50%" } },
          xaxis: { crosshairs: { width: 1 } },

          stroke: {
            show: true,
            curve: "smooth",
            lineCap: "butt",
            colors: undefined,
            width: 1,
            dashArray: 0,
          },

          tooltip: {
            // enabled: false,
            fixed: { enabled: !1 },
            x: { show: !1 },
            y: {
              title: {
                formatter: function (e) {
                  return "";
                },
              },
            },
            marker: { show: !1 },
          },

          states: {
            hover: {
              filter: {
                type: "none",
                value: 0,
              },
            },
          },
        },
        chart2 = new ApexCharts(
          document.querySelector(".area-chart-2"),
          options2
        );
      chart2.render();
    };
    var areaChart3 = function () {
      var options3 = {
          series: [
            {
              data: [
                1.128307699, 1.428307699, 1.228307699, 1.328307699, 1.2124344,
                1.4283077, 1.32830745, 1.528307699, 1.428312, 1.4383234,
                1.32830745, 1.628307699, 1.128307699,
              ],
            },
          ],
          colors: ["#25C866"],
          chart: {
            type: "area",
            Width: 390,
            height: 205,
            sparkline: { enabled: !0 },
          },
          plotOptions: { bar: { columnWidth: "50%" } },
          xaxis: { crosshairs: { width: 1 } },

          stroke: {
            show: true,
            curve: "smooth",
            lineCap: "butt",
            colors: undefined,
            width: 1,
            dashArray: 0,
          },

          tooltip: {
            // enabled: false,
            fixed: { enabled: !1 },
            x: { show: !1 },
            y: {
              title: {
                formatter: function (e) {
                  return "";
                },
              },
            },
            marker: { show: !1 },
          },

          states: {
            hover: {
              filter: {
                type: "none",
                value: 0,
              },
            },
          },
        },
        chart3 = new ApexCharts(
          document.querySelector(".area-chart-3"),
          options3
        );
      chart3.render();
    };
    var areaChart4 = function () {
      var options4 = {
          series: [
            {
              data: [
                1.128307699, 1.428307699, 1.228307699, 1.328307699, 1.2124344,
                1.4283077, 1.32830745, 1.528307699, 1.428312, 1.4383234,
                1.32830745, 1.628307699, 1.128307699,
              ],
            },
          ],
          colors: ["#25C866"],
          chart: {
            type: "area",
            Width: 390,
            height: 205,
            sparkline: { enabled: !0 },
          },
          plotOptions: { bar: { columnWidth: "50%" } },
          xaxis: { crosshairs: { width: 1 } },

          stroke: {
            show: true,
            curve: "smooth",
            lineCap: "butt",
            colors: undefined,
            width: 1,
            dashArray: 0,
          },

          tooltip: {
            // enabled: false,
            fixed: { enabled: !1 },
            x: { show: !1 },
            y: {
              title: {
                formatter: function (e) {
                  return "";
                },
              },
            },
            marker: { show: !1 },
          },

          states: {
            hover: {
              filter: {
                type: "none",
                value: 0,
              },
            },
          },
        },
        chart4 = new ApexCharts(
          document.querySelector(".area-chart-4"),
          options4
        );
      chart4.render();
    };
    var areaChart5 = function () {
      var options5 = {
          series: [
            {
              data: [
                1.128307699, 1.428307699, 1.228307699, 1.328307699, 1.2124344,
                1.4283077, 1.32830745, 1.528307699, 1.428312, 1.4383234,
                1.32830745, 1.628307699, 1.128307699,
              ],
            },
          ],
          colors: ["#25C866"],
          chart: {
            type: "area",
            Width: 390,
            height: 205,
            sparkline: { enabled: !0 },
          },
          plotOptions: { bar: { columnWidth: "50%" } },
          xaxis: { crosshairs: { width: 1 } },

          stroke: {
            show: true,
            curve: "smooth",
            lineCap: "butt",
            colors: undefined,
            width: 1,
            dashArray: 0,
          },

          tooltip: {
            // enabled: false,
            fixed: { enabled: !1 },
            x: { show: !1 },
            y: {
              title: {
                formatter: function (e) {
                  return "";
                },
              },
            },
            marker: { show: !1 },
          },

          states: {
            hover: {
              filter: {
                type: "none",
                value: 0,
              },
            },
          },
        },
        chart5 = new ApexCharts(
          document.querySelector(".area-chart-5"),
          options5
        );
      chart5.render();
    };
    var areaChart6 = function () {
      var options6 = {
          series: [
            {
              data: [
                1.128307699, 1.428307699, 1.228307699, 1.328307699, 1.2124344,
                1.4283077, 1.32830745, 1.528307699, 1.428312, 1.4383234,
                1.32830745, 1.628307699, 1.128307699,
              ],
            },
          ],
          colors: ["#25C866"],
          chart: {
            type: "area",
            Width: 390,
            height: 205,
            sparkline: { enabled: !0 },
          },
          plotOptions: { bar: { columnWidth: "50%" } },
          xaxis: { crosshairs: { width: 1 } },

          stroke: {
            show: true,
            curve: "smooth",
            lineCap: "butt",
            colors: undefined,
            width: 1,
            dashArray: 0,
          },

          tooltip: {
            // enabled: false,
            fixed: { enabled: !1 },
            x: { show: !1 },
            y: {
              title: {
                formatter: function (e) {
                  return "";
                },
              },
            },
            marker: { show: !1 },
          },

          states: {
            hover: {
              filter: {
                type: "none",
                value: 0,
              },
            },
          },
        },
        chart6 = new ApexCharts(
          document.querySelector(".area-chart-6"),
          options6
        );
      chart6.render();
    };
    /* Function ============ */
    return {
      init: function () {},

      load: function () {
        areaChart1();
        areaChart2();
        areaChart3();
        areaChart4();
        areaChart5();
        areaChart6();

      },
      resize: function () {},
    };
  })();

  jQuery(document).ready(function () {});

  jQuery(window).on("load", function () {
    tfAreaChart.load();
  });

  jQuery(window).on("resize", function () {});
})(jQuery);
