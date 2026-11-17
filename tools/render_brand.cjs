// Build-time only: rendered derivatives from precise linked SVG layouts.
const fs=require('node:fs/promises');
const path=require('node:path');
const sharp=require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES?path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES,'sharp'):'sharp');
const root=path.resolve(__dirname,'../hub/web/brand');
async function main(){
  if(process.argv[2])await sharp(process.argv[2]).resize(1920,1080,{fit:'cover'}).jpeg({quality:90}).toFile(path.join(root,'room.jpg'));
  if(process.argv[3])await sharp(process.argv[3]).resize({width:1536,withoutEnlargement:true}).jpeg({quality:92}).toFile(path.join(root,'identity-board.jpg'));
  const badge=(await fs.readFile(path.join(root,'badge.png'))).toString('base64');
  const room=(await fs.readFile(path.join(root,'room.jpg'))).toString('base64');
  for(const name of ['starting','brb','ending','podcast-cover','clip-frame','lower-third','channel-banner','thumbnail-template']){
    let source=await fs.readFile(path.join(root,name+'.svg'),'utf8');
    source=source.replaceAll('href="badge.png"','href="data:image/png;base64,'+badge+'"').replaceAll('href="room.jpg"','href="data:image/jpeg;base64,'+room+'"');
    const renderer=sharp(Buffer.from(source));
    if(['podcast-cover','clip-frame','lower-third'].includes(name))await renderer.png().toFile(path.join(root,name+'.png'));
    else await renderer.jpeg({quality:90}).toFile(path.join(root,name+'.jpg'));
  }
}
main().catch(error=>{process.stderr.write(error.message+'\n');process.exitCode=1;});
