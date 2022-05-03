// Based on Blender source. Original: blender/source/blender/gpu/shaders/gpu_shader_2D_line_dashed_uniform_color_vert.glsl
uniform mat4 ModelViewProjectionMatrix;
uniform vec4 color;
uniform vec2 viewport_size;
in vec2 pos;
flat out vec4 color_vert;
noperspective out vec2 stipple_pos;
flat out vec2 stipple_start;
void main()
{
  gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
  stipple_start = stipple_pos = viewport_size * 0.5 * (gl_Position.xy / gl_Position.w);
  color_vert = color;
}