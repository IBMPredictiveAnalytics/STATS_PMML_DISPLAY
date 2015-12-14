begin program.
import STATS_PMML_DISPLAY
reload(STATS_PMML_DISPLAY)
end program.

file handle models /name="c:/spss21proj/models".

STATS PMML DISPLAY FILES="models/regsim.xml".

STATS PMML DISPLAY FILES="models/logistic.xml".



TMS BEGIN /destination outfile="models/atransf.xml".
compute manager = jobcat > 2.
compute theroot = sqrt(salary).
compute themean = (salary + salbegin)/2.
tms end.

NOMREG manager (BASE=LAST ORDER=ASCENDING) BY jobcat WITH prevexp jobtime
  /CRITERIA CIN(95) DELTA(0) MXITER(100) MXSTEP(5) CHKSEP(20) LCONVERGE(0) PCONVERGE(0.000001) 
    SINGULAR(0.00000001)
  /MODEL
  /STEPWISE=PIN(.05) POUT(0.1) MINEFFECT(0) RULE(SINGLE) ENTRYMETHOD(LR) REMOVALMETHOD(LR)
  /INTERCEPT=INCLUDE
  /PRINT=PARAMETER SUMMARY LRT CPS STEP MFI
  /OUTFILE MODEL('c:\spss21proj\models\mlogistic.xml').

tms merge /destination outfile="models/mlogisticmerged.xml"
/transformations infile="models/atransf.xml"
/model infile='c:\spss21proj\models\mlogistic.xml'.

* mn logistic with transformations.
stats pmml display files="models/mlogisticmerged.xml".
* Cox regression.
stats pmml display files="models/coxreg.xml".

TMS BEGIN /destination outfile="models/complextransf.xml".
compute age = bdate.
compute manager = jobcat > 2 and salary > 50000 or age gt 50.
compute theroot = sqrt(salary).
compute themean = (salary * 2 + salbegin * 5)/2.5.
RECODE educ (Lowest thru 12=1) (Lowest thru 16=2) (Lowest thru 100=3) INTO educrecode.
tms end.
stats pmml display files="models/complextransf.xml".

stats pmml display files="c:/spss21proj/models/complextransf.xml".


* Generalized Linear Models.
GENLIN salary BY educ jobcat (ORDER=ASCENDING) WITH salbegin prevexp
  /MODEL educ jobcat salbegin prevexp INTERCEPT=YES
 DISTRIBUTION=NORMAL LINK=IDENTITY
  /CRITERIA SCALE=MLE COVB=MODEL PCONVERGE=1E-006(ABSOLUTE) SINGULAR=1E-012 ANALYSISTYPE=3(WALD) 
    CILEVEL=95 CITYPE=WALD LIKELIHOOD=FULL
  /MISSING CLASSMISSING=EXCLUDE
  /PRINT CPS DESCRIPTIVES MODELINFO FIT SUMMARY SOLUTION
  /OUTFILE MODEL='c:\spss21proj\models\genlinLinear.xml'.

stats pmml display files="models/genlinLinear.xml".

TWOSTEP CLUSTER
  /CATEGORICAL VARIABLES=educ gender
  /CONTINUOUS VARIABLES=prevexp salary
  /DISTANCE LIKELIHOOD
  /NUMCLUSTERS AUTO 15 BIC
  /HANDLENOISE 0
  /MEMALLOCATE 64
  /CRITERIA INITHRESHOLD(0) MXBRANCH(8) MXLEVEL(3)
  /OUTFILE MODEL='c:\spss21proj\models\twostepSimple.xml'
  /VIEWMODEL DISPLAY=YES.

stats pmml display files = "models\twostepSimple.xml".

* Decision Tree.
TREE salary [s] BY jobcat [o] educ [s] jobtime[s] gender[n]
  /TREE DISPLAY=TOPDOWN NODES=STATISTICS BRANCHSTATISTICS=YES NODEDEFS=YES SCALE=AUTO
  /PRINT MODELSUMMARY RISK
  /GAIN SUMMARYTABLE=YES TYPE=[NODE] SORT=DESCENDING CUMULATIVE=NO
  /SAVE NODEID PREDVAL
  /METHOD TYPE=CHAID
  /GROWTHLIMIT MAXDEPTH=AUTO MINPARENTSIZE=30 MINCHILDSIZE=20
  /VALIDATION TYPE=CROSSVALIDATION(10) OUTPUT=BOTHSAMPLES
  /CHAID ALPHASPLIT=0.05 ALPHAMERGE=0.05 SPLITMERGED=NO ADJUST=BONFERRONI INTERVALS=10
  /OUTFILE TRAININGMODEL='c:\spss21proj\models\treetraining.xml'.

stats pmml display files="models/treetraining.xml".

* neural networks.
stats pmml display files="models/neuralnet_mlp.xml".
stats pmml display files="models/neuralnet_rbf.xml".

* only transformations.
stats pmml display files="models/atransf.xml".

* ruleset.
stats pmml display files="models/ruleset.xml".

*discriminant.
stats pmml display files="models/discriminant.xml".

stats pmml display files="models/genlinPoisson.xml".


DISCRIMINANT
  /GROUPS=jobcat(1 3)
  /VARIABLES=jobtime prevexp educ
  /ANALYSIS ALL
  /OUTFILE=MODEL('models\multidiscrim.xml')
  /PRIORS SIZE 
  /CLASSIFY=NONMISSING POOLED.
stats pmml display files="models/multidiscrim.xml".

* LINEAR pmml (not supported in simulation).
stats pmml display files="models/file_no_key.xml".

* Bad filespec.
stats pmml display files="c:/temp/foo.foo".

* every model.
stats pmml display files="models/*.xml".

stats pmml display files="models/foreign/*.xml".


