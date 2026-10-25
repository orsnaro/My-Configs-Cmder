// The water the dashboard rises out of: the whole screen goes a little darker and deeper-coloured, more towards its edges, as a
// pool does seen from above. It does not read what is behind; how the tiles look under the surface is underwater.wgsl's. (The tiles'
// glass bends the desktop through it: what it bends is what is behind the shell, its own drawing taken out.)
//
// s.a.x how much water there is (0: none; 1: all of it)
// s.color its colour

fn shade(s: Shader) -> vec4<f32> {
    let cen = s.size * 0.5;
    let r = length((s.pos - cen) / cen);
    let a = s.a.x * (0.30 + 0.16 * smoothstep(0.2, 1.4, r));
    return vec4<f32>(s.color.rgb, a);
}
