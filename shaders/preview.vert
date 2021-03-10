in vec2 pos;
in vec2 texCoord;

out vec2 uvInterp;

void main()
{
    uvInterp = texCoord;
    gl_Position = vec4(pos, 0.0, 1.0);
}