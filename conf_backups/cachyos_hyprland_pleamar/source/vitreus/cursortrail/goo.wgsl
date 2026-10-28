// The gooey trail: blobs blurred into each other, then cut sharp again. s.a.x is the blur's reach in pixels.
fn shade(s: Shader) -> vec4<f32> {
    let r = s.a.x;
    let c0 = inside(s, s.pos);
    var acc = c0.a * 2.0;
    var rgb = c0.rgb * c0.a * 2.0;
    var wsum = c0.a * 2.0;
    var total = 2.0;
    for (var ring = 0; ring < 2; ring = ring + 1) {
        let rr = r * (0.5 + 0.5 * f32(ring));
        for (var i = 0; i < 8; i = i + 1) {
            let a = (f32(i) + 0.5 * f32(ring)) * 0.785398;
            let c = inside(s, s.pos + vec2<f32>(cos(a), sin(a)) * rr);
            acc = acc + c.a;
            rgb = rgb + c.rgb * c.a;
            wsum = wsum + c.a;
            total = total + 1.0;
        }
    }
    acc = acc / total;
    let a = smoothstep(0.30, 0.44, acc);
    return vec4<f32>(rgb / max(wsum, 0.0001), a);
}
