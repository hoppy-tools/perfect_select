// Based on Blender source. Original: blender/source/blender/gpu/shaders/gpu_shader_2D_line_dashed_frag.glsl

uniform float dash_width;
uniform float dash_factor;
uniform int colors_len;
uniform vec4 colors[32];
flat in vec4 color_vert;
noperspective in vec2 stipple_pos;
flat in vec2 stipple_start;
out vec4 fragColor;
void main()
{
  float distance_along_line = distance(stipple_pos, stipple_start);
  if (colors_len > 0) {
    if (colors_len == 1) {
      fragColor = colors[0];
    }
    else {
      float normalized_distance = fract(distance_along_line / dash_width);
      fragColor = colors[int(normalized_distance * colors_len)];
    }
  }
  else {
    if (dash_factor >= 1.0f) {
      fragColor = color_vert;
    }
    else {
      float normalized_distance = fract(distance_along_line / dash_width);
      if (normalized_distance <= dash_factor) {
        fragColor = color_vert;
      }
      else {
        discard;
      }
    }
  }
}