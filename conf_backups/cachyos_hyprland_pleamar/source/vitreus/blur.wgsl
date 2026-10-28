// The frosting behind the glass: a gaussian at half size, across and then down, as wide as the Glass page's blur slider says
// (`s.a.x`, 0 to 1). pleamar's own is a fixed one; this is the same shape with a strength. The glass bends a picture of the
// wallpaper (`lens = image`), so what the slider cannot do on the compositor's blur it does here.
fn sigma(s: Blur) -> f32 {
    return mix(0.8, 9.0, clamp(s.a.x, 0.0, 1.0)) * s.scale;
}
fn weight(s: Blur, k: i32) -> f32 {
    let g = sigma(s);
    return exp(-f32(k * k) / (2.0 * g * g));
}
fn wide(s: Blur) -> vec4<f32> {
    let r = i32(ceil(sigma(s) * 2.5));
    var total = vec4<f32>(0.0);
    var sum = 0.0;
    for (var k = -r; k <= r; k++) {
        let w = weight(s, k);
        total += input(s, s.uv + vec2<f32>(f32(k) / s.size.x, 0.0)) * w;
        sum += w;
    }
    return total / sum;
}
fn tall(s: Blur) -> vec4<f32> {
    let r = i32(ceil(sigma(s) * 2.5));
    var total = vec4<f32>(0.0);
    var sum = 0.0;
    for (var k = -r; k <= r; k++) {
        let w = weight(s, k);
        total += prev(s, s.uv + vec2<f32>(0.0, f32(k) / s.size.y)) * w;
        sum += w;
    }
    return total / sum;
}
