import sys
import shutil
import cPickle
import traceback
import os, os.path
import time
import screed
from screed import ScreedDB
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash

app = Flask(__name__)
app.config.from_object('squidlet_config')
app.debug = True

import blastparser

'''
The main index function
Check if the user is logged in; if so, send them on to the main page
'''
@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('query.html', error=None, dbs = app.config['DB'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

"""
Intercepts the form data and splits processes for BLAST
First it splits off a child process
Then it receives the pid of that process, which will be used to check the status of the worker
Then it redirects to the results page, sending the child pid
"""
@app.route('/submit')
def submit():
    if request.method == "POST" and isset(request.form['input']) and isset(request.form['sequence']) and isset(request.form['species']):
        name = request.form['name']
        if not name.strip():
            name = 'query'        
        seqtype = request.form['input']
        sequence = request.form['sequence']
        species = request.form['species']

        tempdir, dirstub = make_dir()

        qf = open("{}/query.fa".format(tempdir))
        qf.write("{}\n{}\n".format(name, sequence))
        qf.close()

        cpid = split_child(worker, (tempdir, species, seqtype))
        print "boom!\nparent pid:{}\nchildpid:{}".format(os.getpid(), cpid)

        return redirect('results/{}'.format(tempdir))
    else:
        return "you don't belong here"

"""
The status checker
First it checks for the existenceo of a file indicating the blast is complete, identified by the child pid
If it doesn't exist, it returns the auto-refreshing template which will call this same function again
If it does exist, it will grab the rendered template produced in the worker
"""
@app.route('/results/<dir>')
def results(fid):
    if os.path.isfile(fid):
        return "yay!"
    return """<head><META http-equiv="refresh" content="5;"></head><body>waiting...:(</body>"""

def worker(tempdir, species, seqtype):
    print "In the worker with pid {}".format(os.getpid())

    pagedump = []
    dbfile = app.config['DB'].getTranscriptomePath(species)
    if dbfile != None:
        o, e, s = manage_blast(dbfile, seqtype, "transcriptome")
        r = list(blastparser.parse_string(o))
        t = render_template("summary.html", results=r, title="mRNA-seq", screedb=s)
        pagedump.append(("mRNA-seq", t))

    dbfile = app.config['DB'].getGenomePath(species)
    if dbfile != None:
        o, e, s = manage_blast(dbfile, seqtype, "genome")
        r = list(blastparser.parse_string(o))
        t = render_template("summary.html", results=r, title="Genome", screedb=s)
        pagedump.append(("Genome", t))

    dbfile = app.config['DB'].getGenePath(species)
    if dbfile != None:
        o, e, s = manage_blast(dbfile, seqtype, "genes")
        r = list(blastparser.parse_string(o))
        t = render_template("summary.html", results=r, title="Gene", screedb=s)
        pagedump.append(("Gene", t))

    output = open('{}/templates.p'.format(tempdir), 'wb')
    cPickle.dump(pagedump, output)
    output.close()

    # kludgy way to shutdown the thread and avoid flask server errors
    os.execlp('touch', 'touch', 'd')

def manage_blast(dbfile, seqtype, outname):

    outname = "{}/{}-out.txt".format(tempdir, outname)
    sdb = ScreedDB(trnsfile)
    qfile = tempdir + '/query.fa'

    if seqtype == 'protein':
        program = 'tblastn'
    else:
        program = 'blastn'
    
    out, err = run_blast(program, newfile, dbfile, args=['-e 1e-6'])

    fp = open(outname, 'w')
    fp.write(out)
    fp.close()

    if err and err.strip():
        fp = open("{}/{}-err.txt".format(tempdir, outname), 'w')
        fp.write(err)
        fp.close()
    
    return out, err, sdb

def run_blast(program, query_file, database_name, args=[]):
    """
    Run BLAST.
    """

    cmd = [ BLAST, '-p', program, '-d', database_name,'-i', query_file ]
    cmd.extend(args)

    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    except OSError:
        return '', traceback.format_exc()
    
    (stdout, stderr) = p.communicate()

    return stdout, stderr

def split_child(child_fn, child_fn_args):
    """
    Fork, and return the child pid to the parent process; in the child process,
    detach from the controlling terminal and *then* run the child fn.
    """
    pid = detach()
    if pid != 0:
        print "Should be non-zero: {}".format(pid)
        return pid
    else:
        print "Should be zero: {}".format(pid)
        child_fn(*child_fn_args)
        
def detach():
    """
    Returns result of os.fork()
    """
    x = os.fork()
    if x != 0:
        return x

    # run in child process; daemonize first
    si = file("/dev/null", 'r')
    so = file("/dev/null", 'a+')
    se = file("/dev/null", 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    os.setsid()

    return x
    
def make_dir():
    """
    Make a working directory.
    """
    dir = tempfile.mkdtemp('', 'blast.', app.config['TEMPDIR'])
    dirstub = dir[len(app.config['TEMPDIR']) + 1:]
    #warning: uncommenting makes the temp directory accessible to all
    #os.chmod(dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    return dir, dirstub
    
def b():    
    fp = open(tempdir + '/index.html', 'w')
    fp.write('<html><head><link rel="stylesheet" type="text/css" href="http://lyorn.idyll.org/~cs.welcher/www/blaststyle.css"></head><body>')
    fp.write('<h1>BLAST complete. </h1>')
    fp.write('<div class="output"><p>See <a href="transcriptome_results.html">mRNAseq blast output.</a></p>')
    fp.write('<p>See <a href="genome_results.html">genome blast output.</a></p>')
    #fp.write('<p>See <a href="blast3-out.txt">predicted genes blast output.</a></p>')
    fp.write('</div>')
    fp.close()

    write_results(tempdir, transcriptome_results, "transcriptome", "blast1-out.txt", seqtype, transcriptomedb)
    write_results(tempdir, genome_results, "genome", "blast2-out.txt", seqtype, genomedb)
    
    return

def write_results(tempdir, results, title, raw_results, seqtype, screeddb):
    fp = open(tempdir + "/" + title + "_results.html", 'w')
    fp.write('<html><head><link rel="stylesheet" type="text/css" href="http://lyorn.idyll.org/~cs.welcher/www/style.css"></head><body>')
    
    fp.write("<div class='section'><h1>" + title + " Results</h1></div><div class='hit'>")
    results_handle = open(tempdir + "/" + raw_results, 'r')
    for i in range(0,19 if seqtype=='protein' else 13):
        fp.write(results_handle.readline() + "<br>")
    fp.write("<p><i>Click for raw <a href='" + raw_results + "'>results</a></i></p></div>")
    fp.write("<div class='section'><h1>" + title + " Summary</h1></div>")

    for record in results:
        #rechtml = '''<div><h2 class='query'>Query: %s</h2>''' % (record.query_name, )
        rechtml = '<div>'
        fp.write(rechtml)
        
        for hit in record.hits:
            hithtml = '''<div class="hit"><h3>Subject: %s</h3>''' % (str(screeddb[hit.subject_name].fullname),)

            fp.write(hithtml)
            for sbm in hit:
                sbmhtml = '''<p>Length: %sbp</p>
                            <p>Score: %s bits</p>
                            <p>Expect: %s</p>
                ''' % ( len(sbm.query_sequence), sbm.score, sbm.expect, )

                
                fp.write(sbmhtml)

                fastaseq = '''<div><h3>FASTA Subject Sequence</h3><textarea class="fastaseq">%s</textarea></div>''' % (">" + str(screeddb[hit.subject_name].fullname) + " " + str(screeddb[hit.subject_name].description)  + "\n" + str(screeddb[hit.subject_name].sequence),)
                fp.write(fastaseq)
                
            fp.write('</div>')
        fp.write('</div>')
    fp.write('</body></html>')
    fp.close()
    return

""" Configuration line should look like:
    <short species name> <full species name> <transcriptome> <genome> <genes>
"""
class DBconf:
    def __init__(self, dbfolder):
        self.folder = dbfolder
        self.dbs = {}
    def readConf(self):
        for dirpath, dirname, filenames in os.walk(self.folder):
            for f in filenames:
                if f == ".about":
                    conf = open(os.path.join(dirpath, f), 'rb')
                    folderkey = os.path.basename(dirpath)
                    self.dbs[folderkey] = {}
                    for line in conf:
                        line = line.split()
                        self.dbs[folderkey][line[0]] = line[1:]
                    
    def getTranscriptomePath(species):
        if dbs.get(species)[0] != "none":
            return dbs.get(species)[0]
        else:
            return None
    def getGenomePath(species):
        if dbs.get(species)[1] != "none":
            return dbs.get(species)[0]
        else:
            return None
    def getGenePath(species):
        if dbs.get(species)[2] != "none":
            return dbs.get(species)[0]
        else:
            return None
   
if __name__ == '__main__':
    app.run()
