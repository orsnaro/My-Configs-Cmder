// The Retro theme's pixelation of a drawer's contents: what the group holds is seen through a grid of squares `s.a.x` px on a side, each one the colour of
// its middle. It is on while a drawer opens or closes (the squares are biggest half way, none at rest), together with the same in the glass (wave.wgsl).
//
// s.a.x the side of a square, in px (1.5 or less: as it is)

fn shade(s: Shader) -> vec4<f32> {
    let k = s.a.x;
    if (k <= 1.5) {
        return inside(s, s.pos);
    }
    let p = (floor(s.pos / k) + vec2<f32>(0.5, 0.5)) * k;
    return inside(s, p);
}
