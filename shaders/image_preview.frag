uniform sampler2D image;
uniform vec4 pattern_color;
uniform float check_size;

in vec2 uvInterp;

float dist(vec2 p0, vec2 pf)
{
    return sqrt((pf.x-p0.x)*(pf.x-p0.x)+(pf.y-p0.y)*(pf.y-p0.y));
}

vec4 checker(vec2 uv, float check_size)
{
  uv -= 0.5;

  float result = mod(floor(check_size * uv.x) + floor(check_size * uv.y), 2.0);
  float fin = sign(result);
  return vec4(fin, fin, fin, 1.0);
}

void main()
{
    vec4 texture_color = texture(image, uvInterp);
    if(texture_color.w == 0.0){
        discard;
    }
    if(texture_color.xyz == vec3(1.0, 1.0, 1.0)) {
        discard;
    }

    vec2 res = vec2(512, 512);
    vec4 final_color = pattern_color;
    float d = dist(res.xy*0.5, gl_FragCoord.xy)*0.001;
    final_color = mix(pattern_color, vec4(pattern_color.xyz*0.3, 1.0), d);

    texture_color = mix(checker(uvInterp, check_size), final_color, 0.9);

    gl_FragColor = texture_color;
}