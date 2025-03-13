if ($(".boarding-swiper").length > 0) {
  var swiperBoarding = new Swiper(".boarding-swiper", {
    speed: 1000,
    parallax: true,
    slidesPerView: "auto",
    spaceBetween: 40,
    // autoplay: true,
    loop: false,
    observer: true,
    observeParents: true,
    pagination: {
      el: ".swiper-pagination",
      clickable: true,
    },
  });
}

if ($(".tf-swiper").length > 0) {
  var spacing = $(".tf-swiper").data("space-between");
  var preview = $(".tf-swiper").data("preview");
  var tablet = $(".tf-swiper").data("tablet");
  var desktop = $(".tf-swiper").data("desktop");
  var swiper4 = new Swiper(".tf-swiper", {
    speed: 1500,
    slidesPerView: preview,
    loop: false,
    spaceBetween: spacing,
    observer: true,
    observeParents: true,

    breakpoints: {
      1024: {
        slidesPerView: desktop,
      },
      768: {
        slidesPerView: tablet,
      },
    },
  });
}



if ($(".market-swiper").length > 0) {
  var spacing = $(" .market-swiper").data("space-between");
  var preview = $(".market-swiper").data("preview");
  var tablet = $(".market-swiper").data("tablet");
  var desktop = $(".market-swiper").data("desktop");
  var swiper4 = new Swiper(".market-swiper", {
    speed: 1500,
    slidesPerView: preview,
    loop: false,
    spaceBetween: spacing,
    observer: true,
    observeParents: true,

    breakpoints: {
      1024: {
        slidesPerView: desktop,
      },
      768: {
        slidesPerView: tablet,
      },
    },
  });
}
